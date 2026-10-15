<div align="center">

# Agentic Travel Planning System

**Chat-first multi-agent AI travel planner with LangGraph orchestration + MCPs.**

![Python 3.12](https://img.shields.io/badge/Python-3.12-blue)
![LangGraph](https://img.shields.io/badge/LangGraph-agent_orchestration-orange)
![FastAPI](https://img.shields.io/badge/FastAPI-backend-009688)
![Vue 3](https://img.shields.io/badge/Vue-3-4FC08D)
![Docker](https://img.shields.io/badge/Docker-compose-2496ED)

</div>

## Key highlights

- **Cost-optimized by design.** Runs on cheap OpenRouter models (`z-ai/glm-5.3-flash`, `gemma-3-12b-it`) and gets its quality from tight LangGraph workflow control instead of raw model size: small scoped prompts, capped input/output tokens per node, deterministic tools for prices/totals.
- **Right model tier per task.** Full model for synthesis, minimal-reasoning for requirements extraction and subagent tool loops, light model for routing fallback — never a big model for a small job. Every call goes through OpenRouter, so models and providers are plain IDs and swappable in one line — no vendor lock-in when something better appears.
- **Parallel multi-agent research.** An orchestrator fans out to 5 specialist ReAct subagents (weather, transport, accommodation, activities, rental cars) running in parallel over MCP tools. A main LLM then gathers the findings into one reply with priced options for the user to pick from.
- **Jev decision-model routing.** The router uses a Jev decision call (with chat-LLM fallback) instead of burning a full generation on every turn — cheaper and faster for a step that only picks the next route.
- **Human-in-the-loop UI.** The agent proposes options, you pick from clickable cards/buttons: destinations and priced options render as choice controls, and your picks are saved deterministically — the LLM confirms, it never invents prices.
- **Observability with LangSmith and cost-per-turn tracing.** LangSmith tracing plus a `stats` event after every turn: tokens in/out, authoritative OpenRouter cost (`cost_usd`) and duration, shown under each assistant message.

<sub>* Per-token cost is roughly 15–20× below frontier flagships (≈ $0.15/$0.50 per 1M in/out for GLM-5.3-Flash depending on provider, vs $2/$10 for GPT-6.1 Sol at current OpenRouter rates).</sub>
<sub>* OpenRouter providers are also pinned per model, cutting both cost and latency versus default routing.</sub>

## Demo

<!-- ![Chat demo](docs/assets/demo.png) -->

> Video walkthrough — coming soon. Working on it.

## What it does

Ask for a trip in plain language. The system researches real options and builds a plan you can adjust:

1. Understands origin, dates, budget, travelers, interests, constraints.
2. Compares candidate destinations, then lets you pick one.
3. Researches flights, hotels, activities, weather and rental cars in parallel via MCP tools.
4. Publishes priced, selectable options per category (transport, stay, activities, rental car).
5. Saves choices deterministically and keeps a running total vs. budget.
6. Saves the finished trip to a plans library you can revisit later.
7. Streams the whole turn over SSE with per-agent status; persists conversations in SQLite.

Example:

> Hi! My partner and I want to get away for about 10 days in mid-September, flying from Madrid. Our budget is around €2,500. We love hiking and nature, and we would rather avoid very touristy places.
> → compares destinations → researches the selected destination → options with prices → plan + €2,180 total.

## Architecture

<img src="docs/images/LangGraph_Workflow.png" width="800">

- One shared LangGraph app built at startup; `thread_id = conversation_id`.
- Destination pick pauses via `interrupt()` and resumes on the next turn; saved-choices confirmations skip extract + router and go straight to main_llm.
- Frontend: Vue 3 chat + requirements panel + plan/budget sidebar + saved-plans library.
- Full graph diagram + node reference: [`docs/architecture.md` §4 LangGraph Workflow](docs/architecture.md#4-langgraph-workflow).

## Tech stack

| Layer | Choice |
|---|---|
| Orchestration | LangGraph (subgraphs per research agent, SQLite checkpointer) |
| LLMs | OpenRouter `z-ai/glm-5.3-flash` (main), `google/gemma-3-12b-it` (light tasks), Jev decision model for routing |
| Backend | FastAPI, SSE streaming, SQLite (`data/app.db` + `data/checkpoints.db`) |
| Travel data (MCP) | `trvl` CLI (flights/hotels/transport), TicketLens (POIs/tours), `weather-mcp` (forecast/history), OctoTrip (rental cars) |
| Frontend | Vue 3 + PrimeVue + Pinia + Vue Router, axios, marked + DOMPurify |
| Deploy | Docker Compose (backend `:8000`, frontend `:8080`) |

## Quickstart

Prereqs: [Docker Desktop](https://www.docker.com/products/docker-desktop/) (or Engine + Compose v2) and an [OpenRouter](https://openrouter.ai/) API key. No local Python/Node needed — everything runs in containers.

```bash
# 1. Secrets (gitignored, never committed)
echo "OPENROUTER_API_KEY=sk-or-v1-..." > .env

# 2. Run
docker compose up --build

# 3. Open
# App: http://localhost:8080
# API docs: http://localhost:8000/docs
```

First backend boot takes ~30s (downloads weather MCP via `npx`, loads all MCP tools).
Watch for `MCP tools ready` + `Graph built` in `docker compose logs backend`.
Data persists in the `backend-data` volume (`down -v` resets it).

Local dev (needs [`uv`](https://docs.astral.sh/uv/) + Node 22+): backend `uv run uvicorn app.main:app --port 8000` from `src/backend` (deps sync automatically);
frontend `npm install && npm run dev` from `src/frontend` (`http://localhost:5173`).

## Project structure

```text
src/
  backend/app/      # FastAPI + LangGraph (agents/, api/v1/, database/, evals/)
  frontend/src/     # Vue 3 (views/, components/, stores/, api/, router/)
docs/architecture.md
docker-compose.yml
```

Legacy `notebooks/` holds the incremental prototypes from the early development phases; `src/` is the current full app. Full breakdown in [`docs/architecture.md` §11 Project Structure](docs/architecture.md#11-project-structure).

## Known issues

- The `trvl` intent `search_hotels` returns very large payloads. The accommodation agent is prompted to prefer `search_accommodations` (leaner) and only fall back to `search_hotels` when it returns nothing useful — but the fallback can still fire and inflate token usage.
- Pulling large historical weather datasets can also return token-heavy responses. The weather subagent is prompted to request only the minimum history window needed, so this is rare.
- The OctoTrip rental-cars MCP goes down occasionally; the graph builds without it and the subagent reports the gap instead of failing the turn.
- Prices and availability come from free MCP tiers, so treat them as indicative rather than exact. A production setup would use paid travel-data providers.

## Future work

- Automated evaluation of conversations and plans (Jev-as-a-judge).
- Migrate SQLite → PostgreSQL or MariaDB.
- Context compaction for very long conversations.

## Author

**Andrés Corbacho Sánchez**
End-to-end design and build: LangGraph orchestration, FastAPI backend, Vue 3 frontend, MCP integrations, Docker deploy.

[![GitHub](https://img.shields.io/badge/GitHub-AndresCorSan-100000?style=for-the-badge&logo=github&logoColor=white)](https://github.com/AndresCorSan)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-andres--corbacho-0A66C2?style=for-the-badge&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/andres-corbacho)

License: MIT (see `LICENSE`).
