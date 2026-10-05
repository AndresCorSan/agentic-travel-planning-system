import asyncio
import logging
import os
from langchain_openrouter import ChatOpenRouter
from pydantic import PrivateAttr

logger = logging.getLogger("uvicorn.error")

# Seconds to wait before retrying a rate-limited model once.
RETRY_DELAY_S = 2.0

def require_openrouter_key() -> str:
    """Read OPENROUTER_API_KEY or fail with an actionable message.

    Replaces bare os.environ[...] (cryptic KeyError at import) and the
    inconsistent os.getenv(...) (None key failing much later): every
    instance fails fast, at startup, with the same clear message.
    """
    key = os.getenv("OPENROUTER_API_KEY")
    if not key:
        raise RuntimeError(
            "OPENROUTER_API_KEY is not set. Add it to the root .env "
            "(see .env.example) and restart the backend."
        )
    return key


# Fallback chain for the lightweight LLM (comma-separated, in order).
# Default: same family upscaled, then MiMo minimal (different provider/model).
LIGHT_LLM_FALLBACKS = [
    m.strip()
    for m in os.getenv(
        "LIGHT_LLM_FALLBACKS",
        "google/gemma-3-27b-it,z-ai/glm-5.3-flash",
    ).split(",")
    if m.strip()
]


def _status_code(exc: Exception) -> int | None:
    return getattr(exc, "status_code", None)


class ResilientChatOpenRouter(ChatOpenRouter):
    """ChatOpenRouter with retry + model fallback on 429s.

    Still a regular chat model, so bind_tools / with_structured_output keep
    working untouched. On rate limits it retries the current model once
    after RETRY_DELAY_S, then rotates through `fallback_models` in order
    (same policy per model). Non-429 errors propagate immediately.

    Note: the model id is swapped on the shared instance (restored in a
    `finally`). Two turns racing a fallback window may briefly answer from
    the fallback model instead of the primary — benign, both are
    configured models.
    """

    _primary_model: str | None = PrivateAttr(default=None)
    _fallback_models: list = PrivateAttr(default_factory=list)

    def __init__(self, *args, fallback_models=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._primary_model = kwargs.get("model")
        self._fallback_models = list(fallback_models or [])

    def _chain(self) -> list:
        models = [self._primary_model]
        models.extend(self._fallback_models)
        return [m for m in models if m]

    def _use_model(self, model: str):
        # `model_name` (alias `model`) is the field the payload is built from.
        try:
            self.model_name = model
        except Exception:
            self.model = model

    def _log_429(self, model: str, attempt: str):
        logger.warning(
            "LLM 429 on %s (%s); %s",
            model,
            attempt,
            "retrying shortly" if attempt == "try" else "switching model",
        )

    async def _generate_resilient(self, *args, **kwargs):
        primary = self._primary_model
        last_exc: Exception | None = None
        try:
            for model in self._chain():
                self._use_model(model)
                for attempt in ("try", "retry"):
                    try:
                        return await super()._agenerate(*args, **kwargs)
                    except Exception as exc:
                        if _status_code(exc) != 429:
                            raise
                        last_exc = exc
                        self._log_429(model, attempt)
                        if attempt == "try":
                            await asyncio.sleep(RETRY_DELAY_S)
            assert last_exc is not None
            raise last_exc
        finally:
            self._use_model(primary)

    async def _stream_resilient(self, *args, **kwargs):
        primary = self._primary_model
        last_exc: Exception | None = None
        yielded = False
        try:
            for model in self._chain():
                self._use_model(model)
                for attempt in ("try", "retry"):
                    try:
                        async for chunk in super()._astream(*args, **kwargs):
                            yielded = True
                            yield chunk
                        return
                    except Exception as exc:
                        if _status_code(exc) != 429:
                            raise
                        # A fallback re-stream would duplicate an already
                        # partially streamed answer: don't retry mid-stream.
                        if yielded:
                            raise
                        last_exc = exc
                        self._log_429(model, attempt)
                        if attempt == "try":
                            await asyncio.sleep(RETRY_DELAY_S)
            assert last_exc is not None
            raise last_exc
        finally:
            self._use_model(primary)

    async def _agenerate(self, *args, **kwargs):
        return await self._generate_resilient(*args, **kwargs)

    async def _astream(self, *args, **kwargs):
        async for chunk in self._stream_resilient(*args, **kwargs):
            yield chunk

# Providers for GLM-5.3-Flash, limited to these five (Together first).
GLM_PROVIDER = {
    "order": ["together", "baseten", "fireworks", "deepinfra", "relace"],
    "allow_fallbacks": False,
}

# Normal LLM (retry once on 429s, no fallback model by decision)
llm = ResilientChatOpenRouter(
    model="z-ai/glm-5.3-flash",
    api_key=require_openrouter_key(),
    openrouter_provider=GLM_PROVIDER,
)

# Low-effort LLM for faster and cheaper responses
low_reasoning_llm = ResilientChatOpenRouter(
    model="z-ai/glm-5.3-flash",
    api_key=require_openrouter_key(),
    openrouter_provider=GLM_PROVIDER,
    reasoning={
        "effort": "minimal",
    },
)

# Lightweight LLM for simple tasks (gemma -> gemma-27b -> mimo minimal)
light_llm = ResilientChatOpenRouter(
    model="google/gemma-3-12b-it",
    api_key=require_openrouter_key(),
    fallback_models=LIGHT_LLM_FALLBACKS,
)
