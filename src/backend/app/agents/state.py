from operator import add
from typing import Annotated, Literal
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field

# Define the shared TravelState
class TravelRequirements(BaseModel):
    origin: str | None = None
    destination: str | None = None
    travel_dates: str | None = None
    duration_days: int | None = None
    travelers: int | None = None
    budget: float | None = None
    currency: str | None = None
    interests: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)

class DestinationCandidate(BaseModel):
    destination: str
    score: float
    reason: str

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

class TravelState(TypedDict):
    messages: Annotated[list, add_messages]
    requirements: TravelRequirements | None
    
    destination_research_needed: bool 
    destination_candidates: list[DestinationCandidate]

    # Results from each sub-agent
    orchestration_plan: list[AgentTask]

    weather_results: Annotated[list, add]
    accommodation_results: Annotated[list, add]
    transportation_results: Annotated[list, add]
    activity_results: Annotated[list, add]
    rental_car_results: Annotated[list, add]
