"""Requirements tool: applies mid-reply requirement updates from the main LLM."""
import json
from langchain.tools import tool, ToolRuntime
from langchain_core.messages import ToolMessage
from langgraph.types import Command
from app.agents.state import TravelRequirements

def _normalize_list(value: list[str] | str | None) -> list[str]:
    """
    Normalize a value into a list of strings.

    Accepts None, an existing list, or a JSON-encoded list returned as a string.
    If the string is not valid JSON, it is treated as a single list item.
    """
    if value is None:
        return []

    if isinstance(value, list):
        return value

    # The model may return the list as a JSON-encoded string.
    if isinstance(value, str):
        try:
            parsed = json.loads(value)

            # Return the parsed value if it is a valid JSON list.
            if isinstance(parsed, list):
                return parsed

        except json.JSONDecodeError:
            pass

        return [value]

    # Fallback for unexpected input types.
    return []


@tool
def update_requirements(
    runtime: ToolRuntime,
    origin: str | None = None,
    destination: str | None = None,
    travel_dates: str | None = None,
    duration_days: int | None = None,
    travelers: int | None = None,
    budget: float | None = None,
    currency: str | None = None,
    transport_mode: str | None = None,
    accommodation_type: str | None = None,
    add_interests: list[str] | str | None = None,
    remove_interests: list[str] | str | None = None,
    add_constraints: list[str] | str | None = None,
    remove_constraints: list[str] | str | None = None,
) -> Command:
    """
    Save the travel requirements from the user's message.

    WHEN TO CALL: when the message adds, changes, or removes travel
    information — stated directly or clearly implied ("my partner" means
    2 travelers, "a week" means 7 days...).

    WHEN NOT TO CALL — do not call this tool at all for:
    - greetings, goodbyes, thanks, small talk ("hi", "hello", "thanks")
    - questions with no travel content

    HOW TO FILL EACH FIELD: normalize the user's wording freely (months
    into dates, "a week" into 7 days, "by train"/"flying"/"driving" into
    transport_mode, "hotel"/"hostel"/"apartment" into accommodation_type...),
    but never invent entities the user
    did not mention: no new cities or destinations, no budget figures,
    no constraints they did not state. When in doubt about a field,
    leave it unset — partial updates are correct.

    For interests and constraints:
    - Use add_interests to add new interests.
    - Use remove_interests to remove previous interests.
    - Use add_constraints to add new constraints.
    - Use remove_constraints to remove previous constraints.

    Do not modify information that the user has not changed.
    """

    # ToolRuntime gives the tool access to the current LangGraph state,
    # including the TravelRequirements stored in the current graph execution.
    current = runtime.state["requirements"]

    if current is None:
        current = TravelRequirements()

    updated = current.model_copy()

    # 1. Normalize list args (the model may send JSON strings).
    add_interests = _normalize_list(add_interests)
    remove_interests = _normalize_list(remove_interests)
    add_constraints = _normalize_list(add_constraints)
    remove_constraints = _normalize_list(remove_constraints)

    # 2. Overwrite only explicitly provided scalar fields.
    if origin is not None:
        updated.origin = origin

    if destination is not None:
        updated.destination = destination

    if travel_dates is not None:
        updated.travel_dates = travel_dates

    if duration_days is not None:
        updated.duration_days = duration_days

    if travelers is not None:
        updated.travelers = travelers

    if budget is not None:
        updated.budget = budget

    if currency is not None:
        updated.currency = currency

    if transport_mode is not None:
        updated.transport_mode = transport_mode

    if accommodation_type is not None:
        updated.accommodation_type = accommodation_type

    # 3. Merge interest/constraint deltas without duplicates.
    if add_interests:
        updated.interests = list(
            dict.fromkeys(
                updated.interests + add_interests
            )
        )

    if remove_interests:
        updated.interests = [
            interest
            for interest in updated.interests
            if interest not in remove_interests
        ]

    if add_constraints:
        updated.constraints = list(
            dict.fromkeys(
                updated.constraints + add_constraints
            )
        )

    if remove_constraints:
        updated.constraints = [
            constraint
            for constraint in updated.constraints
            if constraint not in remove_constraints
        ]

    # Command tells LangGraph to update the graph state.
    # The new TravelRequirements replaces the current "requirements" value.
    return Command(
        update={
            "requirements": updated,
            "messages": [
                ToolMessage(
                    content="Travel requirements updated successfully.",
                    tool_call_id=runtime.tool_call_id,
                )
            ],
        }
    )
