# Travel Intelligence Agent

> An agentic AI travel planner built with LangGraph, LangChain, and MCP.

## Overview

Travel Intelligence Agent is a web application that helps users research
and plan trips from natural-language requirements.

Instead of asking the user to search flights, hotels, activities,
weather, and transportation separately, the system coordinates these
sources, compares alternatives, builds a personalized itinerary, and
checks whether the result actually satisfies the user's constraints.

The project is being developed incrementally, starting with a simple
LLM-based travel planner and progressively adding external MCPs, custom
tools, LangGraph orchestration, persistence, observability, and
evaluation.

## What It Does

The final system will be able to:

-   Understand travel preferences and constraints expressed in natural
    language.
-   Compare candidate destinations.
-   Research flights, accommodation, transportation, weather, and
    activities.
-   Build a personalized day-by-day itinerary.
-   Estimate and validate the total trip budget.
-   Consider practical constraints such as dates and transportation
    requirements.
-   Review the generated plan before presenting it.
-   Replan when the proposed trip does not satisfy the user's
    requirements.
-   Provide evidence behind important recommendations.

## Example

**User**

> I want to travel for 10 days in September with my partner, leaving
> from Madrid. Our budget is €2,500. We like hiking and nature, want to
> avoid very touristy places, and don't want to rent a car.

**Travel Intelligence Agent**

> I've compared several destinations. Madeira is currently the best
> match for your requirements.
>
> Estimated trip cost: €2,180
>
> Why it fits: - Excellent hiking opportunities - Suitable September
> weather - Within budget - Possible to travel without renting a car
>
> Main drawback: some hiking areas have limited public transport.
>
> I can now build a 10-day itinerary based on these requirements.

The user can then change a requirement, for example:

> What if we increase the budget to €3,000?

The system can use the existing travel state and replan rather than
starting from scratch.

## Architecture

The application is built around a small number of focused components:

-   **Travel Planner Agent** --- understands requirements, selects
    destinations, coordinates research, and builds the travel plan.
-   **Travel Critic Agent** --- reviews the proposed plan and determines
    whether it satisfies the user's requirements.
-   **LangGraph** --- orchestrates the workflow, manages shared state,
    parallel research, conditional routing, and replanning.
-   **MCP** --- provides standardized access to external travel
    capabilities.
-   **Custom tools** --- handle deterministic application logic such as
    budget calculation and constraint validation.

The detailed architecture, workflow, persistence model, integrations,
and design decisions are documented in
[`architecture.md`](./docs/architecture.md).

## MCP Integrations

The project is intentionally built around a combination of external and
custom MCP servers.

| MCP | Purpose |
|---|---|
| Weather MCP | Weather forecasts and historical weather |
| trvl MCP | Flights, hotels, trains, buses, ferries, and rental cars |
| TicketLens MCP | Activities, attractions, and experiences |
| Custom Maps MCP | Geocoding, places, routes, distances, and travel times |

The project also uses regular application tools for deterministic
operations such as budget calculation, constraint validation, and trip
scoring.

## Tech Stack

| Technology | Role |
|---|---|
| Python | Core application |
| LangGraph | Agent orchestration and workflow |
| LangChain | LLM and tool integration |
| MCP | External tool interoperability |
| FastAPI | Backend API |
| Vue.js | Web application |
| MariaDB | Application persistence |
| LangSmith | Observability and evaluation |

## Development Progress

The project is developed incrementally. Each phase adds a meaningful
capability to the system.

### Phase 1 — Initial Travel Agent

- [x] Create the basic LLM chat loop
- [x] Add the initial system prompt
- [x] Refine the Travel Planner's personality and tone
- [x] Test and refine the agent with realistic travel scenarios

### Phase 2 — Structured Travel State

- [x] Define the initial `TravelState`
- [x] Make the Travel Planner produce structured requirements
- [x] Store the structured requirements in the graph state
- [x] Add LangGraph checkpointing
- [x] Verify that travel state persists across interactions
- [x] Verify that travel state updates when needed

### Phase 3 — External Capabilities

- [x] Integrate the Weather MCP into the existing graph
- [x] Use weather data in destination recommendations
- [x] Integrate the trvl MCP
- [x] Use real travel data in the planning process
- [x] Integrate the TicketLens MCP
- [x] Use activity data in destination recommendations
- [x] Integrate the OctoTrip Rental Cars MCP
- [x] Use rental car data in destination recommendations

### Phase 4 — Destination Research

- [x] Add an initial requirements extraction node
- [x] Add router node for deciding whether destination research is needed
- [x] Generate a shortlist of candidate destinations
- [x] Score and compare candidate destinations
- [x] Let the user select one of those destinations

### Phase 5 — Parallel Multi-Agent Research

- [x] Orchestrate specialized travel-research subagents and execute them in parallel
- [x] Implement iterative MCP tool use within each subagent and store their results in the shared state
- [x] Pass the available research results to the main LLM for final synthesis

### Phase 6 — Plan & Budget

- [x] Define the structured travel-plan representation
- [ ] Generate a complete plan from the research results
- [ ] Add deterministic budget calculation

### Phase 7 — Critic & Replanning

- [ ] Add the Travel Critic Agent
- [ ] Connect the critic to the generated travel plan
- [ ] Route valid plans to the final response
- [ ] Route invalid plans back to the Travel Planner
- [ ] Implement bounded replanning
- [ ] Test the planner with conflicting and unsatisfied requirements

### Phase 8 — Conversational Web Prototype

- [x] Create initial frontend prototype
- [x] Expose the LangGraph workflow through a minimal web interface
- [x] Build the conversational chat interface
- [x] Support multi-turn conversations and LangGraph interrupts/resume
- [x] Display subagents responses as complementary info
- [ ] Support thread-based conversations
- [x] Display current travel requirements and planning state
- [x] Let users pick research options in the chat (human-in-the-loop implementation)
- [x] Display trip plan and budget information
- [ ] Allow saving the current trip plan to the "Saved plans" library

### Phase 9 — Persistence & Production Backend

- [ ] Persist users, sessions, requirements, research, and trip plans in MariaDB
- [ ] Add production-oriented LangGraph checkpointing
- [x] Expose the planning workflow through FastAPI
- [ ] Connect the web application to persistent backend data

### Phase 10 — Observability, Evaluation & Release

- [ ] Integrate LangSmith tracing
- [ ] Create a representative evaluation dataset
- [ ] Add automated evaluation of generated plans
- [ ] Evaluate constraint satisfaction and recommendation quality
- [ ] Evaluate groundedness and replanning behavior
- [ ] Measure latency, token usage, and tool usage
- [ ] Add unit and integration tests
- [ ] Improve error handling and edge cases
- [ ] Optimize latency and cost
- [ ] Complete documentation and architecture diagrams
- [ ] Add deployment configuration
- [ ] Deploy a public demo
- [ ] Publish the first release

## Project Structure

The repository structure will evolve as development progresses. The
intended high-level structure is:

``` text
travel-intelligence-agent/
├── src/
|   ├── frontend/
|   └── backend/
├── mcp/
├── tests/
├── evaluation/
├── docs/
├── README.md
└── ...
```

## Documentation

-   [`architecture.md`](./architecture.md) --- system architecture,
    agents, LangGraph workflow, MCPs, persistence, frontend,
    observability, evaluation, and development phases.

## Project Status

This project is under active development. The architecture is defined,
but implementation is being built incrementally so that each major
capability can be developed and evaluated independently.

## License

To be defined.
