from langchain_core.messages import SystemMessage
from app.agents.llm import low_reasoning_llm
from app.agents.state import TravelRequirements, TravelState
from app.agents.utils import sanitize_messages_for_llm

REQUIREMENTS_EXTRACTION_PROMPT = """
Extract the user's explicit travel requirements into the provided schema.

Only include information explicitly stated by the user.
Do not infer preferences, constraints, destinations, dates, budgets, or other values.

Preserve the user's meaning when normalizing values such as dates and currency.
Leave unknown fields empty.
"""

requirements_llm = low_reasoning_llm.with_structured_output(
    TravelRequirements
)

async def extract_requirements(state: TravelState):
    response = await requirements_llm.ainvoke([
        SystemMessage(content=REQUIREMENTS_EXTRACTION_PROMPT),
        *sanitize_messages_for_llm(state["messages"]),
    ])

    return {"requirements": response}