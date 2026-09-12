# Travel Intelligence Agent — Architecture

## 1. Overview

Travel Intelligence Agent is an AI-powered travel research and planning
assistant.

The system helps users find and plan trips based on their personal preferences,
constraints, and objectives. Instead of simply generating an itinerary, the
agent researches real-world travel options, compares alternatives, validates
constraints, and replans when necessary.

The system is built around **LangGraph** for agent orchestration and
**Model Context Protocol (MCP)** for accessing external travel capabilities.

---

## 2. Problem

Planning a trip requires combining information from multiple sources:

- Flights
- Accommodation
- Transportation
- Weather
- Activities
- Destinations

Current travel platforms are good at searching individual components, but
users still have to manually combine this information and determine which
option best fits their specific constraints.

The goal is to provide a single agentic system capable of performing this
research and producing a coherent, personalized travel plan.

---

## 3. Goals

- Understand natural-language travel requirements.
- Research and compare multiple destinations.
- Use real-world travel data through MCP tools.
- Respect user constraints such as budget, dates and transportation.
- Generate personalized itineraries.
- Validate proposed plans before presenting them.
- Replan when constraints cannot be satisfied.
- Provide evidence for important recommendations.
- Maintain travel-planning state across interactions.

---

## 4. Example User Interaction

**User**

> I want to travel for 10 days in September with my partner, leaving from
> Madrid. Our budget is €2,500. We like hiking and nature, want to avoid very
> touristy places, and don't want to rent a car.

**Agent**

> I've compared 12 destinations. My top recommendation is Madeira (91/100).
>
> Estimated cost: €2,180
>
> Why:
> - Excellent hiking opportunities
> - Suitable September weather
> - Fits your budget
> - Possible to travel without renting a car
>
> Main drawback: some hiking areas have limited public transport.
>
> I can now build a 10-day itinerary for Madeira.

The user can then modify the requirements:

> What if we increase the budget to €3,000?

The system updates the existing state and replans instead of starting from
scratch.

---

## 5. High-Level Architecture

<img src="./images/high-level-architecture.png" width="700">


---

## 6. Agents

### Travel Planner Agent

The main agent responsible for understanding the user's requirements,
selecting the most suitable destination, coordinating travel research, and
building the final travel plan.

It can:

- Interpret user preferences and constraints.
- Identify and compare candidate destinations.
- Decide which information needs to be researched.
- Combine flight, accommodation, activity, and transportation options.
- Build and optimize the travel plan.
- Trigger replanning when the current plan does not satisfy the requirements.

The agent uses external capabilities through MCP tools and does not directly
handle provider-specific integrations.

### Travel Critic Agent (discarded)

> **Design decision (evaluated, not implemented):** an LLM-based critic with
> a bounded planner → critic → replan loop was considered and deliberately
> discarded:
>
> - **Latency/cost** — every turn pays at least one extra LLM call (more on
>   replan), very noticeable in an interactive chat.
> - **False positives** — the critic can misread a requirement and reject a
>   valid plan, triggering a "repair" that makes the result worse.
> - **Unnecessary by design** — the system is human-in-the-loop: the agent
>   proposes researched options with live prices and totals, and the user
>   chooses. The failure mode the critic exists for (the agent deciding
>   badly on its own) does not occur here; validation happens in the UI,
>   where the user sees totals vs. budget and picks accordingly.
> - **Low demo value** — the visible output (a "valid" badge) duplicates
>   what the user already sees in the trip-plan panel.
>
> End-to-end testing showed the planner already produces
> constraint-satisfying plans reliably, so a critic loop adds cost without
> measurable benefit.

---

## 7. LangGraph Workflow

LangGraph orchestrates the complete planning process and manages the shared
state between the agents, tools, and deterministic components.

The main workflow is:

```text
User Request
     │
     ▼
Travel Planner Agent
     │
     │ Select destination
     ▼
Destination Research
     │
     ├──────────┬───────────┬────────────┐
     ▼          ▼           ▼            ▼
  Flights     Hotels    Activities   Transport
     │          │           │            │
     └──────────┴───────────┴────────────┘
                       │
                       ▼
                  Plan Builder
                    + Budget
                       │
                       ▼
              Travel Critic Agent
                       │
                 ┌─────┴─────┐
                 │           │
               Valid       Invalid
                 │           │
                 ▼           ▼
           Final Response   Replan
                             │
                             ▼
                    Travel Planner Agent
                             │
                             └──► Research
```

If the critic determines that the plan does not satisfy the user's
requirements, LangGraph routes execution back to the Travel Planner Agent,
which can modify the plan and repeat the necessary research.

The number of replanning attempts is bounded to prevent uncontrolled loops.

LangGraph is responsible for workflow orchestration, shared state,
parallel execution, conditional routing, and replanning.

---

## 8. Tools & MCP

The system uses **MCP for external travel capabilities** and custom tools for
internal deterministic logic.

### External MCPs

#### [Weather MCP](https://github.com/weather-mcp/weather-mcp)

Provides weather information used to evaluate destinations and build
weather-aware itineraries.

Main capabilities:

* Weather forecasts
* Historical weather
* Location search

#### [trvl MCP](https://github.com/MikkoParkkola/trvl)

Provides travel search capabilities across multiple transportation and
accommodation categories.

Main capabilities:

* Flights
* Hotels
* Trains
* Buses
* Ferries

#### [TicketLens MCP](https://github.com/ticketlens/ticketlens-experiences-mcp)

Provides activity and ticket information for destinations.

Main capabilities:

* Search activities
* Search attractions and experiences
* Retrieve activity details

#### [OctoTrip Rental Cars MCP](https://github.com/OctoTrip/rental-cars)

Provides rental car information for destinations.

Main capabilities:

* Search rental cars
* Compare rental offers and prices

---

### Custom Tools

Some capabilities do not require MCP and will be implemented as regular
application tools or deterministic code:

* `calculate_budget()` — calculates the estimated total trip cost.
* `validate_constraints()` — checks hard constraints such as budget, dates,
  duration, and transportation requirements.
* `calculate_trip_score()` — evaluates candidate plans according to the user's
  preferences and requirements.

The distinction is intentional: **MCP is used for external capabilities that
benefit from a standardized tool interface, while internal business logic is
implemented directly as application tools.**

---

## 9. Persistence

**MariaDB** will store application data such as:

- Users
- Travel sessions
- Travel requirements
- Research results
- Evidence
- Itineraries

**LangGraph checkpointing** will be used to persist graph execution state,
allowing conversations and travel-planning workflows to continue across
interactions.

Application data and LangGraph execution state will be treated as separate
concerns.

---

## 10. Web Application

The application will use **Vue.js** for the frontend and **FastAPI** for the
backend API.

The web application will provide:

- **Chat** — interact with the travel agent.
- **Destination comparison** — compare recommended destinations.
- **Interactive map** — visualize destinations, activities, and routes.
- **Itinerary** — view the generated trip day by day.
- **Budget** — visualize estimated costs.
- **Evidence** — inspect the sources behind important recommendations.

FastAPI will act as the main backend API between the Vue.js frontend and the
agentic system, while LangGraph manages the travel-planning workflow.

---

## 11. Observability

The system will use **LangSmith** to monitor and debug agent executions.

Tracked information will include:

* LangGraph runs
* Node execution
* MCP/tool calls
* Errors
* Latency
* Token usage
* Estimated cost

---

## 12. Evaluation

The system will include a reproducible evaluation dataset containing realistic
travel requests and constraints.

Key metrics:

* **Constraint satisfaction** — does the plan respect user requirements?
* **Recommendation quality** — are destinations relevant?
* **Groundedness** — are important claims supported by retrieved data?
* **Replanning success** — can the agent recover from an invalid plan?
* **Tool efficiency** — does the agent use tools appropriately?
* **Latency and cost** — how expensive and slow is a planning session?

---

## 13. Development Phases

### Phase 1 — Initial Travel Agent
- Build a simple LLM-based Travel Planner.
- Define system prompt, personality, tone, and response format.
- Test with realistic travel scenarios.

### Phase 2 — Structured Travel State
- Define the shared `TravelState`.
- Extract and maintain structured user requirements.
- Update the `TravelState` accross interactions.

### Phase 3 — External Capabilities
- Integrate Weather MCP.
- Build the custom Maps MCP.
- Integrate trvl MCP.
- Integrate TicketLens MCP.
- Evaluate the impact of external data on recommendations.

### Phase 4 — Destination Research
- Implement candidate destination generation.
- Research and compare destinations.
- Select the most suitable destination.

### Phase 5 — Parallel Multi-Agent Research
- Orchestrate specialized travel-research agents.
- Execute selected agents in parallel and collect their results.
- Synthesize specialist research with the main Travel Planner.

### Phase 6 — Plan & Budget
- Define the structured travel-plan representation.
- Generate a complete itinerary from the research results.
- Implement deterministic budget calculation.
- Implement constraint validation.
- Implement trip scoring and plan selection.

### Phase 7 — Critic & Replanning
- Introduce the Travel Critic Agent.
- Evaluate generated travel plans against requirements.
- Add conditional routing and bounded replanning loops.
- Refine plans when constraints are violated or recommendations are weak.

### Phase 8 — Conversational Web Prototype
- Expose the LangGraph workflow through a minimal web interface.
- Build a conversational chat interface for multi-turn planning.
- Support LangGraph interrupts, resume, and thread-based conversations.
- Display the current travel requirements and planning state for debugging.
- Display itinerary, budget, validation, and research results.
- Use the prototype as the main environment for end-to-end testing.

### Phase 9 — Persistence & Production Backend
- Add MariaDB persistence.
- Integrate production-oriented LangGraph checkpointing.
- Persist users, sessions, requirements, research, and itineraries.
- Build the production FastAPI backend.
- Connect the web application to persistent data.

### Phase 9 — Observability & Evaluation
- Integrate LangSmith.
- Build an evaluation dataset.
- Measure constraint satisfaction, groundedness,
  recommendation quality, and replanning success.

### Phase 10 — Observability, Evaluation & Release
- Integrate LangSmith tracing.
- Build an evaluation dataset.
- Measure constraint satisfaction, groundedness, recommendation quality,
  replanning success, latency, token usage, and tool usage.
- Add unit and integration tests.
- Improve error handling and edge cases.
- Optimize latency and cost.
- Complete documentation and architecture diagrams.
- Add deployment configuration.
- Deploy and publish the project.

