from operator import add
from typing import Annotated, Literal
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field, field_validator

# Define the shared TravelState
class TravelRequirements(BaseModel):
    origin: str | None = Field(default=None, description="Place the trip starts from (the location in 'from ...'). Null if not stated.")
    destination: str | None = Field(default=None, description="Main place to visit (the location in 'to ...'). Null if not stated.")
    travel_dates: str | None = Field(default=None, description="Explicit dates or date range as written by the user. Null if not stated.")
    duration_days: int | None = Field(default=None, description="Trip length in days as an integer. Null if not stated.")
    travelers: int | None = Field(default=None, description="Number of travelers as an integer. Null if not stated.")
    budget: float | None = Field(default=None, description="Max budget as a plain number, no currency symbols. Null if not stated.")
    currency: str | None = Field(default=None, description="3-letter currency code for the budget. Null if not stated, never guessed.")
    transport_mode: str | None = Field(default=None, description="How they travel: bus, train, flight, car, etc. Null if not stated.")
    accommodation_type: str | None = Field(default=None, description="Where they stay: hotel, hostel, apartment, etc. Null if not stated.")
    interests: list[str] = Field(default_factory=list, description="Thematic interests as short keywords (beach, gastronomy, hiking). Logistics never go here.")
    constraints: list[str] = Field(default_factory=list, description="Only genuine restrictions with no dedicated field (budget-friendly, no flights, ...). Never duplicate facts from other fields.")

    @field_validator(
        "origin",
        "destination",
        "travel_dates",
        "currency",
        "transport_mode",
        "accommodation_type",
        mode="before",
    )
    @classmethod
    def _blank_str_to_none(cls, v):
        if v is None:
            return None
        if isinstance(v, str) and v.strip().lower() in ("", "none", "null", "n/a"):
            return None
        return v

    @field_validator("duration_days", "travelers", "budget", mode="before")
    @classmethod
    def _blank_num_to_none(cls, v):
        if v is None:
            return None
        if isinstance(v, str) and v.strip().lower() in ("", "none", "null", "n/a"):
            return None
        return v

class DestinationCandidate(BaseModel):
    destination: str
    score: float
    reason: str
    country: str = ""
    country_code: str = ""
    highlights: list[str] = Field(default_factory=list)
    drawback: str = ""

class AgentTask(BaseModel):
    agent: Literal[
        "weather_agent",
        "accommodation_agent",
        "transportation_agent",
        "activities_agent",
        "rental_cars_agent",
    ]
    task: str

class OrchestrationPlan(BaseModel):
    tasks: list[AgentTask]

class PlanOption(BaseModel):
    """One selectable option presented by main_llm for a category.

    Stored in state so both UI buttons (by id) and chat choices (by LLM
    matching) resolve against the same canonical list.

    `group` splits a category into independently selectable legs (e.g.
    transportation "outbound" vs "return", or "leg 1" vs "leg 2" of a
    flight+bus combo). Empty means the whole category is one group.
    """

    id: str
    label: str
    price: float | None = None
    currency: str | None = None
    per_person: bool = False
    details: str = ""
    group: str = Field(default="", description="Selectable leg within the category ('outbound', 'return', 'leg 1'...). Empty means the category's single default group.")

class PlanItem(BaseModel):
    """A user choice saved into the trip plan.

    Snapshots label/price at save time so later overwrites of
    available_options (new searches) never break the plan.
    """

    category: str
    option_id: str
    label: str
    price: float | None = None
    currency: str | None = None
    per_person: bool = False
    details: str = ""
    group: str = ""

# Categories where a new choice replaces the previous one (vs activities,
# which accumulates). The replacement key is (category, group), so legs
# like transportation "outbound"/"return" are independent. Must stay in
# sync with the main_llm prompt.
SINGLE_CHOICE_CATEGORIES = ("transportation", "accommodation", "rental_car")


def get_field(obj, name: str, default=None):
    """Read a field from a pydantic model or a plain dict.

    Graph state mixes both shapes after `aupdate_state`, so every mapper
    needs this instead of its own `getattr or .get` lambda.
    """
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def _norm_group(value) -> str:
    """Canonical group label: stripped + lowercase.

    Groups come from the LLM ("Outbound" vs "outbound") and act as
    replacement keys in add/merge — normalize once so casing never
    splits a leg in two. Display re-capitalizes (frontend groupLabel).
    """
    return str(value or "").strip().lower()


def _opt_group(opt) -> str:
    return _norm_group(get_field(opt, "group"))


def _merge_options(
    left: dict | None, right: dict | None
) -> dict[str, list["PlanOption"]]:
    """Merge per-category option dicts.

    main_llm calls present_options once per category in the same turn, so
    several parallel tool writes land on this channel in one step. A plain
    LastValue channel rejects that (InvalidUpdateError); merging by
    category key lets each call contribute its own category.

    Within a category, merging is per group: a republish replaces only
    the options of its own group (e.g. a fresh "outbound" search keeps
    the published "return" options).
    """
    merged = dict(left or {})
    if right:
        for category, opts in right.items():
            incoming = list(opts or [])
            incoming_groups = {_opt_group(o) for o in incoming}
            kept = [o for o in (merged.get(category) or []) if _opt_group(o) not in incoming_groups]
            merged[category] = kept + incoming
    return merged

class TravelState(TypedDict):
    messages: Annotated[list, add_messages]
    requirements: TravelRequirements | None
    
    next_step: Literal["destination_research", "orchestrator", "main_llm"] | None
    destination_candidates: list[DestinationCandidate]

    # Results from each sub-agent
    orchestration_plan: list[AgentTask]

    weather_results: Annotated[list, add]
    accommodation_results: Annotated[list, add]
    transportation_results: Annotated[list, add]
    activity_results: Annotated[list, add]
    rental_car_results: Annotated[list, add]

    # Selectable options per category + the user's saved trip plan
    available_options: Annotated[dict, _merge_options]
    trip_plan: list[PlanItem]

    # One usage entry per LLM call in the turn (see `usage.py`). Needed
    # because structured outputs and subagents leave no AIMessage in
    # `messages`. Entry: {node, model, input_tokens, output_tokens,
    # total_tokens, cost_usd}. Grows across turns; `conversations._stream`
    # slices from a snapshot length and aggregates with `sum_entries`.
    turn_usage: Annotated[list, add]
