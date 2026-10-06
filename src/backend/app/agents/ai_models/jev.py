"""TypeSafe Jev decision model (System One, not an LLM) via OpenRouter.

Jev answers narrow, typed questions about a state instead of generating
text. Called through OpenRouter's Decisions API with the same
OPENROUTER_API_KEY — no separate TypeSafe key needed.
"""

import logging
import os

logger = logging.getLogger("uvicorn.error")

JEV_MODEL = "typesafe/jev-1.13"
JEV_CONFIDENCE_THRESHOLD = 0.6
JEV_TIMEOUT_S = 5.0
JEV_DECISIONS_URL = "https://openrouter.ai/api/alpha/decisions"


async def decide_route_via_jev(
    state: str | dict,
    instructions: str,
    criteria: dict,
    question_key: str = "route",
) -> tuple[str, float] | None:
    """Ask Jev for a routing decision.

    Returns None when misconfigured, so the caller falls back to the chat
    LLM, or on any transport/schema error.

    Args:
        state: Conversation or graph state Jev decides about.
        instructions: Decision question instructions sent to Jev.
        criteria: Allowed choices keyed by choice name.
        question_key: Key identifying the decision question in the payload.

    Returns:
        The chosen route with its confidence, or None when falling back.
    """
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        logger.warning("Jev skipped: OPENROUTER_API_KEY not set")
        return None
    try:
        import httpx

        payload = {
            "model": JEV_MODEL,
            "state": state,
            "questions": {
                question_key: {
                    "type": "choice",
                    "instructions": instructions,
                    "criteria": criteria,
                }
            },
        }
        async with httpx.AsyncClient(timeout=JEV_TIMEOUT_S) as client:
            resp = await client.post(
                JEV_DECISIONS_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
        answer = (data.get("answers") or {}).get(question_key) or {}
        choice = answer.get("choice")
        confidence = float(answer.get("confidence", 0.0) or 0.0)
        usage = data.get("usage") or {}
        logger.info(
            "Jev decision: %s (confidence=%.2f, cost=%s)",
            choice,
            confidence,
            usage.get("cost"),
        )
        if choice not in criteria:
            logger.warning("Jev returned unknown choice: %r", choice)
            return None
        return choice, confidence
    except Exception:
        logger.warning("Jev call failed; falling back to chat LLM", exc_info=True)
        return None
