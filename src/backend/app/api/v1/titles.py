"""Auto-titling for conversations via light_llm.

The title is generated once, after the graph runs, and only when the
turn carries enough context (a bare "hi" must not freeze the title).
Manual renames leave the AUTO_TITLES set, so they are never overwritten.
Any LLM failure returns None: the previous title is kept.
"""
import json

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.ai_models import light_llm
from app.agents.usage import message_usage

AUTO_TITLES = ("New trip", "Untitled trip")

TITLE_SYSTEM_PROMPT = (
    "Generate a short chat title for a travel-planning conversation. "
    "Rules: max 45 characters, plain text, no quotes, no emoji, no trailing period. "
    "Write it in the same language as the user's last message. "
    "Describe the trip (destination and/or theme), not the literal message. "
    "Reply with the title only, nothing else."
)


def has_title_context(message: str, requirements, candidates) -> bool:
    """True once there is enough substance to generate a title once."""
    if candidates:
        return True
    if requirements is not None:
        get = lambda name: getattr(requirements, name, None) if not isinstance(requirements, dict) else requirements.get(name)
        scalar = any(get(n) for n in ("origin", "destination", "travel_dates", "duration_days", "travelers", "budget", "currency", "transport_mode", "accommodation_type"))
        if scalar:
            return True
        for n in ("interests", "constraints"):
            v = get(n)
            if isinstance(v, list) and any(str(x).strip() for x in v):
                return True
    text = (message or "").strip().lower()
    if len(message.strip()) < 12:
        return False
    greetings = ("hi", "hello", "hey", "hola", "buenas", "buenos dias", "buenos días", "buenas tardes", "buenas noches", "que tal", "qué tal")
    if any(text == g or text.startswith(g + " ") or text.startswith(g + ",") for g in greetings) and len(text) < 30:
        return False
    return True


async def generate_title(message: str, requirements, candidates) -> tuple[str | None, dict | None]:
    """Ask light_llm for a short conversation title.

    Returns (title, usage_entry) so the caller can fold this call into
    the turn's stats. Any failure returns (None, None).
    """
    try:
        lines = [f"Last user message: {message.strip()[:500]}"]
        if requirements is not None:
            dump = requirements.model_dump() if hasattr(requirements, "model_dump") else dict(requirements)
            compact = {k: v for k, v in dump.items() if v}
            if compact:
                lines.append(f"Requirements: {json.dumps(compact, ensure_ascii=False)[:800]}")
        if candidates:
            names = []
            for c in candidates[:5]:
                get = lambda n: getattr(c, n, None) if not isinstance(c, dict) else c.get(n)
                name = get("destination")
                if name:
                    names.append(str(name))
            if names:
                lines.append(f"Candidate destinations: {', '.join(names)}")
        msg = await light_llm.ainvoke([
            SystemMessage(content=TITLE_SYSTEM_PROMPT),
            HumanMessage(content="\n".join(lines)),
        ])
        usage = message_usage(msg, "title")
        title = str(getattr(msg, "content", "") or "").strip().strip("\"'“”‘’").strip()
        if not title or len(title) > 60:
            title = title[:60].strip()
        if not title:
            return None, usage
        return title, usage
    except Exception:
        return None, None
