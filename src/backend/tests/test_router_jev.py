"""Router tests: Jev (via OpenRouter Decisions API) + chat-LLM fallback.

Run from `src/backend` so `app.*` imports resolve::

    uv run pytest tests/test_router_jev.py -v -s

`test_router_live[...]`: 10 real prompts through `research_router`.
Needs `OPENROUTER_API_KEY` (each call costs a fraction of a cent);
skipped automatically without it.

Last live run: 2026-09-23 — 10/10 passed, all decided by Jev directly
(no fallback used). Confidences 0.93-1.00, except the honeymoon case
which first scored 0.67: its wording overlapped main_llm ("stating a
travel intent...") and destination_research. After sharpening both
JEV_ROUTE_CRITERIA (explicit idea/recommendation triggers on
destination_research, "without asking for anything" guard on main_llm),
it re-tested at 1.00. Cost ~$0.000021 per call.
"""

import asyncio
import logging
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

try:  # Let live tests pick up the repo-root .env without exporting the key.
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parents[3] / ".env")
except ImportError:  # pragma: no cover
    pass

LIVE = bool(os.getenv("OPENROUTER_API_KEY"))
# llm.py reads OPENROUTER_API_KEY at import time; the dummy only serves the
# offline wiring tests (live tests are skipped without a real key).
os.environ.setdefault("OPENROUTER_API_KEY", "offline-dummy-key")

from langchain_core.messages import HumanMessage  # noqa: E402

from app.agents.nodes import router as router_mod
from app.agents.nodes.router import research_router
from app.agents.state import TravelRequirements

LIVE = bool(os.getenv("OPENROUTER_API_KEY"))
requires_key = pytest.mark.skipif(not LIVE, reason="OPENROUTER_API_KEY not set")


def _state(text: str) -> dict:
    return {
        "messages": [HumanMessage(content=text)],
        "requirements": TravelRequirements(),
    }


# (user prompt, expected next_step)
LIVE_CASES = [
    # main_llm: greetings / small talk / intent without a concrete ask
    ("Hi, how are you?", "main_llm"),
    ("Thanks for the help", "main_llm"),
    ("I want to travel to Japan in spring", "main_llm"),
    ("What do you know about Kyoto in autumn?", "main_llm"),
    # destination_research: no single destination committed
    (
        "I can't decide between Paris, Rome or Barcelona, which do you recommend?",
        "destination_research",
    ),
    (
        "Compare Lisbon with Porto for a quiet week-long trip",
        "destination_research",
    ),
    ("Looking for honeymoon destination ideas in September", "destination_research"),
    # orchestrator: concrete, bookable options for a planned trip
    (
        "Find cheap hotels in Madrid from October 10 to 15",
        "orchestrator",
    ),
    (
        "I need flights from Bilbao to Rome for two people in December",
        "orchestrator",
    ),
    (
        "Find activities and tours in New York for 3 days",
        "orchestrator",
    ),
]


@requires_key
@pytest.mark.parametrize("prompt,expected", LIVE_CASES)
def test_router_live(prompt, expected, caplog):
    with caplog.at_level(logging.INFO, logger="uvicorn.error"):
        result = asyncio.run(research_router(_state(prompt)))
    jev = [r.getMessage() for r in caplog.records if "Jev decision" in r.getMessage()]
    detail = "; ".join(jev) if jev else "fallback LLM (Jev failed/low-confidence)"
    print(f"\n{prompt!r} -> {result['next_step']} (expected {expected}) [{detail}]")
    assert result["next_step"] == expected


def test_jev_high_confidence_skips_fallback_llm(monkeypatch):
    """A confident Jev answer must be used directly (no chat-LLM call)."""

    async def fake_jev(**kwargs):
        return ("orchestrator", 0.95)

    async def exploding_fallback(*args, **kwargs):
        raise AssertionError("fallback LLM must not be called")

    monkeypatch.setattr(router_mod, "decide_route_via_jev", fake_jev)
    monkeypatch.setattr(
        router_mod, "structured_router_llm", SimpleNamespace(ainvoke=exploding_fallback)
    )
    result = asyncio.run(research_router(_state("find hotels in Madrid")))
    assert result == {"next_step": "orchestrator"}


def test_jev_low_confidence_falls_back_to_llm(monkeypatch):
    """A low-confidence Jev answer must defer to the chat LLM."""

    async def fake_jev(**kwargs):
        return ("orchestrator", 0.1)

    async def fake_llm(*args, **kwargs):
        # include_raw=True contract: raw/parsed/parsing_error dict.
        return {"raw": None, "parsed": SimpleNamespace(route="main_llm"), "parsing_error": None}

    monkeypatch.setattr(router_mod, "decide_route_via_jev", fake_jev)
    monkeypatch.setattr(
        router_mod, "structured_router_llm", SimpleNamespace(ainvoke=fake_llm)
    )
    result = asyncio.run(research_router(_state("hi there")))
    assert result == {"next_step": "main_llm", "turn_usage": []}


def test_jev_error_falls_back_to_llm(monkeypatch):
    """A Jev transport failure (None) must defer to the chat LLM."""

    async def fake_jev(**kwargs):
        return None

    async def fake_llm(*args, **kwargs):
        # include_raw=True contract: raw/parsed/parsing_error dict.
        return {"raw": None, "parsed": SimpleNamespace(route="destination_research"), "parsing_error": None}

    monkeypatch.setattr(router_mod, "decide_route_via_jev", fake_jev)
    monkeypatch.setattr(
        router_mod, "structured_router_llm", SimpleNamespace(ainvoke=fake_llm)
    )
    result = asyncio.run(research_router(_state("Paris or Rome, which to pick?")))
    assert result == {"next_step": "destination_research", "turn_usage": []}
