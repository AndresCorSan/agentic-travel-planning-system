from langchain_core.messages import HumanMessage, SystemMessage
from app.agents.llm import low_reasoning_llm
from app.agents.state import TravelRequirements, TravelState
from app.agents.tools.plan import SAVED_CHOICES_PREFIX
from app.agents.utils import current_date_message, sanitize_messages_for_llm

REQUIREMENTS_EXTRACTION_PROMPT = """
Extract the user's explicit travel requirements into the provided schema.

Only include information explicitly stated by the user.
Do not infer preferences, constraints, destinations, dates, budgets, or other values.

Preserve the user's meaning when normalizing values such as dates and currency.
Map "by train"/"flying"/"driving" style statements to transport_mode and
"hotel"/"hostel"/"apartment" mentions to accommodation_type.
Leave unknown fields empty.
Use JSON null for unknown fields — never the string "None".

Never write a conversational reply or any text outside the schema.
Your only output is the structured requirements object — always return it,
even if all fields are empty.
"""

requirements_llm = low_reasoning_llm.with_structured_output(
    TravelRequirements
)

async def extract_requirements(state: TravelState):
    messages = state.get("messages") or []
    # Saved-choices confirmations carry no new requirements and already
    # updated the plan deterministically: skip the LLM call entirely.
    if messages and isinstance(messages[-1], HumanMessage) and str(messages[-1].content or "").startswith(SAVED_CHOICES_PREFIX):
        return {}
    response = await requirements_llm.ainvoke([
        SystemMessage(content=REQUIREMENTS_EXTRACTION_PROMPT),
        current_date_message(),
        *sanitize_messages_for_llm(state["messages"]),
    ])

    return {"requirements": response}