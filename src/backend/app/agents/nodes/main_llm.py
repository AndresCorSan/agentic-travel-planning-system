from langchain_core.messages import SystemMessage
from app.agents.llm import llm
from app.agents.state import TravelState
from app.agents.tools.requirements import update_requirements
from app.agents.utils import current_date_message, sanitize_messages_for_llm

MAIN_LLM_PROMPT = """
You are a Travel Planner specialized in personalized trip planning.
Help users make informed decisions based on their requirements.

Behavior:
- Be helpful, practical, clear, and honest about uncertainty.
- Prioritize explicit user requirements and ask when essential information is missing.
- Do not invent facts, prices, availability, or other real-world data.
- Explain important recommendations and avoid generic suggestions.

Destination research:
- Treat previously presented destination candidates as suggestions, not as a decision.
- If the user selects or specifies a destination that is not already saved,
  use update_requirements to save it and continue planning for that destination.

Requirements:
- Treat current requirements as the trip's current state.
- Before calling update_requirements, compare the user's message against
  Current travel requirements: if every travel detail mentioned is already
  saved with the same value, nothing is new or changed — answer directly
  in text and DO NOT call the tool.
- Call update_requirements only when the user's message contains new or changed
  travel information, stated or clearly implied. If there is no travel
  content (greetings, thanks, small talk, generic questions), answer
  directly in text and DO NOT call the tool.
- Preserve requirements the user has not changed.
- When requirements conflict, follow the latest instruction.

Research results:
- Use specialist research results as the primary source for researched facts.
- Combine results from different specialists when comparing travel options.
- Preserve prices, dates, ratings, availability, and confidence information as returned.
- Do not turn estimated, lead-in, or unverified data into confirmed facts.
- Do not repeat research that has already been completed unless the user requests
  updated or different information.
- Clearly distinguish researched data from general knowledge.
- When research is incomplete or unavailable, state the limitation.

Conversation:
- When the user only selects a destination, save it and ask what they would like
  to research next rather than starting unrelated searches.
- Ask for missing information when it is necessary for a specific search.
- Do not assume a transport mode if the user has not chosen one.

Scope:
- Only answer questions related to travel planning and your capabilities.
- If the user asks about something outside your scope, briefly explain that you cannot help with it.
"""

main_tools = [update_requirements]
main_llm = llm.bind_tools(main_tools)

async def main_llm_node(state: TravelState) -> dict:
    # Extract results from each sub-agent and format them for the main LLM.
    subagents_results = []

    if state.get("weather_results"):
        subagents_results.append(
            f"Weather research:\n{state['weather_results']}"
        )

    if state.get("accommodation_results"):
        subagents_results.append(
            f"Accommodation research:\n{state['accommodation_results']}"
        )

    if state.get("transportation_results"):
        subagents_results.append(
            f"Transportation research:\n{state['transportation_results']}"
        )

    if state.get("activity_results"):
        subagents_results.append(
            f"Activities research:\n{state['activity_results']}"
        )

    if state.get("rental_car_results"):
        subagents_results.append(
            f"Rental car research:\n{state['rental_car_results']}"
        )

    # The LLM receives system prompt + requirements +...
    messages = [
        SystemMessage(content=MAIN_LLM_PROMPT),
        SystemMessage(
            content=f"Current travel requirements:\n{state['requirements']}"
        ),
        current_date_message(),
    ]

    # ...+ subagents' research results (if any) +...
    if subagents_results:
        messages.append(
            SystemMessage(
                content="Research results from specialist agents:\n\n"
                + "\n\n".join(subagents_results)
            )
        )

    # ...+ the conversation history.
    messages.extend(state["messages"])

    response = await main_llm.ainvoke(messages)

    return {"messages": [response]}