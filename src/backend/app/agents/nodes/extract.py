"""Requirements extraction node: parses the turn into `TravelRequirements`.

UI choice confirmations skip the LLM call for this requirements extraction
(the plan was already updated deterministically). 
Unparseable output keeps the previous requirements.
"""
from langchain_core.messages import SystemMessage
import logging
from app.agents.ai_models import llm
from app.agents.state import TravelRequirements, TravelState
from app.agents.tools.plan import is_ui_choices_confirmation
from app.agents.usage import collect_usage
from app.agents.utils import current_date_message, sanitize_messages_for_llm

logger = logging.getLogger("uvicorn.error")

REQUIREMENTS_EXTRACTION_PROMPT = """
Extract the user's travel requirements into the provided schema as a
complete merged object.

You receive Previously saved requirements plus the conversation history.
Start from the previously saved requirements, then apply only the
new or changed information from the user's latest message.
Preserve every previously saved field the user has not changed or
explicitly removed. Anaphoric references ("those dates", "there",
"from there") resolve against the saved requirements and history.

Only include information explicitly stated by the user in the current
or past messages. Do not infer preferences, constraints, destinations,
dates, budgets, or other values.

Set a previously saved field back to null ONLY when the user explicitly
removes or cancels it ("forget the budget", "dates are flexible now"...).
A field merely absent from the latest message is never a removal.

Preserve the user's meaning when normalizing values such as dates and currency.
Map logistics to their dedicated fields, never to constraints or interests:
- "to <place>" goes to destination; "from <place>" goes to origin.
- "by <means>" ("by train", "flying", "driving"...) goes to transport_mode ("train", "flight", "car"...); 
any lodging noun ("hotel", "hostel", "apartment", "guesthouse"/"guesthouses", "villa", "cabin", "lodge", "bnb"...) 
goes to accommodation_type as a short noun ("guesthouse"). Qualifiers ("quiet", "nature-oriented") 
go as separate one-word constraints, never as a sentence inside constraints.
- "<N> travelers/people" goes to travelers (integer); "<N>-night/<N>-day trip" goes to duration_days (integer).
- Explicit dates go to travel_dates; an amount with currency goes to budget + currency.
interests holds only thematic keywords (beach, gastronomy, hiking...).
constraints holds only short keyword restrictions with no dedicated field (budget-friendly, no flights, quiet...): one fact per entry.

Never repeat the same fact in two fields.
If no amount was ever stated, leave budget AND currency null — never guess them.

Example: previously saved origin "Porto", user now says "Cheap 2-night
food trip to Lisbon by train, 2 travelers" becomes origin "Porto"
(preserved), destination "Lisbon", duration_days 2, travelers 2,
transport_mode "train", interests ["food"], constraints ["cheap"].
Fields with nothing ever stated stay null.
Use JSON null for unknown fields — never the string "None".

For interests and constraints return the full merged lists (previously
saved items plus newly stated ones, minus items the user explicitly
removed).

Never write a conversational reply or any text outside the schema.
Your only output is the structured requirements object — always return
the full merged object, even if all fields are empty.
"""

requirements_llm = llm.with_structured_output(
    TravelRequirements,
    # Keep the raw response for turn usage stats; parse errors still raise.
    include_raw=True,
)

# Scalar fields: a parsed None means "not mentioned", never a removal —
# the previous value is kept (explicit removals are handled by main_llm
# via update_requirements, not by extract).
_SCALAR_FIELDS = (
    "origin",
    "destination",
    "travel_dates",
    "duration_days",
    "travelers",
    "budget",
    "currency",
    "transport_mode",
    "accommodation_type",
)

def _merge_requirements(previous, parsed: TravelRequirements) -> TravelRequirements:
    """Merge a parsed delta over the previously saved requirements.

    Scalars: parsed non-None wins, otherwise the previous value is kept.
    Lists (interests/constraints): union of previous + parsed, deduped in
    order, so a partial LLM delta never drops earlier items.

    Args:
        previous: Previously saved requirements (model, dict, or None).
        parsed: Fresh LLM output treated as a delta.

    Returns:
        Merged TravelRequirements.
    """
    if previous is None:
        return parsed
    prev_data = (
        previous.model_dump() if isinstance(previous, TravelRequirements) else dict(previous)
    )
    new_data = parsed.model_dump()
    merged = dict(new_data)
    for field in _SCALAR_FIELDS:
        if merged.get(field) is None:
            merged[field] = prev_data.get(field)
    for field in ("interests", "constraints"):
        old_items = [str(x).strip() for x in (prev_data.get(field) or []) if str(x).strip()]
        new_items = [str(x).strip() for x in (merged.get(field) or []) if str(x).strip()]
        merged[field] = old_items + [x for x in new_items if x not in old_items]
    return TravelRequirements(**merged)


async def extract_requirements(state: TravelState, config: dict | None = None):
    """Extract structured travel requirements from the latest turn.

    Skips the LLM call for UI choice confirmations and keeps the previous
    requirements when the model output is unparseable.

    Args:
        state: Current graph state holding messages and requirements.
        config: Optional LangGraph invoke config carrying the thread id.

    Returns:
        Partial state update with requirements and turn usage, usage only
        when output is unparseable, or empty update when skipped.
    """
    messages = state.get("messages") or []
    # Saved-choices confirmations carry no new requirements and already
    # updated the plan deterministically: skip the LLM call entirely.
    if is_ui_choices_confirmation(messages):
        return {}
    previous = state.get("requirements")
    result = await requirements_llm.ainvoke([
        SystemMessage(content=REQUIREMENTS_EXTRACTION_PROMPT),
        SystemMessage(
            content=f"Previously saved requirements:\n{previous if previous is not None else 'none yet'}"
        ),
        current_date_message(),
        *sanitize_messages_for_llm(state["messages"]),
    ])
    if result.get("parsing_error") is not None:
        logger.warning("Requirements extraction unparseable; keeping previous")
        return {"turn_usage": collect_usage([result["raw"]], "extract_requirements")}

    req = _merge_requirements(previous, result["parsed"])
    filled = {k: v for k, v in req.model_dump().items() if v}
    logger.info(
        "[%s] extract: requirements %s",
        (config or {}).get("configurable", {}).get("thread_id", "?"),
        filled,
    )
    return {
        "requirements": req,
        "turn_usage": collect_usage([result["raw"]], "extract_requirements"),
    }