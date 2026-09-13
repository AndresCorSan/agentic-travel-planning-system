from operator import add
from typing import Annotated, Literal
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field, field_validator

# Define the shared TravelState
class TravelRequirements(BaseModel):
    origin: str | None = None
    destination: str | None = None
    travel_dates: str | None = None
    duration_days: int | None = None
    travelers: int | None = None
    budget: float | None = None
    currency: str | None = None
    transport_mode: str | None = None
    accommodation_type: str | None = None
    interests: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)

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
    """

    id: str
    label: str
    price: float | None = None
    currency: str | None = None
    per_person: bool = False
    details: str = ""

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

# Categories where a new choice replaces the previous one (vs activities,
# which accumulates). Must stay in sync with the main_llm prompt.
SINGLE_CHOICE_CATEGORIES = ("transportation", "accommodation", "rental_car")


def _merge_options(
    left: dict | None, right: dict | None
) -> dict[str, list["PlanOption"]]:
    """Merge per-category option dicts.

    main_llm calls present_options once per category in the same turn, so
    several parallel tool writes land on this channel in one step. A plain
    LastValue channel rejects that (InvalidUpdateError); merging by
    category key lets each call contribute its own category.
    """
    merged = dict(left or {})
    if right:
        merged.update(right)
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
