from langchain_core.messages import SystemMessage
import logging
from app.agents.ai_models import low_reasoning_llm
from app.agents.state import TravelRequirements, TravelState
from app.agents.tools.plan import is_ui_choices_confirmation
from app.agents.usage import collect_usage
from app.agents.utils import current_date_message, sanitize_messages_for_llm

logger = logging.getLogger("uvicorn.error")

REQUIREMENTS_EXTRACTION_PROMPT = """
Extract the user's explicit travel requirements into the provided schema.

Only include information explicitly stated by the user.
Do not infer preferences, constraints, destinations, dates, budgets, or other values.

Preserve the user's meaning when normalizing values such as dates and currency.
Map logistics to their dedicated fields, never to constraints or interests:
- "to <place>" goes to destination; "from <place>" goes to origin.
- "by <means>" ("by train", "flying", "driving"...) goes to transport_mode ("train", "flight", "car"...); "hotel"/"hostel"/"apartment" mentions go to accommodation_type.
- "<N> travelers/people" goes to travelers (integer); "<N>-night/<N>-day trip" goes to duration_days (integer).
- Explicit dates go to travel_dates; an amount with currency goes to budget + currency.
interests holds only thematic keywords (beach, gastronomy, hiking...).
constraints holds only restrictions with no dedicated field (budget-friendly, no flights, ...).
Never repeat the same fact in two fields.
If no amount is stated, leave budget AND currency null — never guess them.

Example: "Cheap 2-night food trip to Lisbon from Porto by train,
2 travelers" becomes origin "Porto", destination "Lisbon",
duration_days 2, travelers 2, transport_mode "train",
interests ["food"], constraints ["cheap"], everything else null.
Leave unknown fields empty.
Use JSON null for unknown fields — never the string "None".

Never write a conversational reply or any text outside the schema.
Your only output is the structured requirements object — always return it,
even if all fields are empty.
"""

requirements_llm = low_reasoning_llm.with_structured_output(
    TravelRequirements,
    # Keep the raw response for turn usage stats; parse errors still raise.
    include_raw=True,
)


async def extract_requirements(state: TravelState, config: dict | None = None):
    messages = state.get("messages") or []
    # Saved-choices confirmations carry no new requirements and already
    # updated the plan deterministically: skip the LLM call entirely.
    if is_ui_choices_confirmation(messages):
        return {}
    result = await requirements_llm.ainvoke([
        SystemMessage(content=REQUIREMENTS_EXTRACTION_PROMPT),
        current_date_message(),
        *sanitize_messages_for_llm(state["messages"]),
    ])
    if result.get("parsing_error") is not None:
        logger.warning("Requirements extraction unparseable; keeping previous")
        return {"turn_usage": collect_usage([result["raw"]], "extract_requirements")}

    req = result["parsed"]
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