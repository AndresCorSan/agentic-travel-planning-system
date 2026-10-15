# AGENTS.md

Monorepo: `src/backend` (FastAPI + LangGraph) + `src/frontend` (Vue 3 + PrimeVue + Pinia). `notebooks/` is the legacy prototype — `src/` is the source of truth. No CI, lint, or formatter; only test is `src/backend/tests/test_router_jev.py` (pytest, configured in root `pyproject.toml`).

## Run

- Primary: `docker compose up --build` from root (app `:8080`, API `:8000/docs`). Secrets from root `.env` (gitignored). Data in `backend-data` volume (`down -v` resets it). First backend boot takes ~30s (weather MCP via `npx`); watch for `MCP tools ready` + `Graph built` in logs.
- Local dev: backend `uv run uvicorn app.main:app --port 8000` from `src/backend` (so `app.*` resolves; deps sync automatically; restart for any `app/` change); frontend `npm install && npm run dev` from `src/frontend` (`:5173`). Needs `uv`, Node 22+, `trvl` CLI on PATH.
- Env: only `OPENROUTER_API_KEY` required (root `.env`, see `.env.example` for optionals: `CORS_ORIGINS`, `LIGHT_LLM_FALLBACKS`, `DATABASE_URL`, `CHECKPOINT_DB_URL`, `LANGSMITH_*`). Frontend `.env` (`VITE_API_BASE_URL=http://localhost:8000/api/v1`) is local-dev only — Docker bakes the URL via build arg. Never commit `.env`.
- Verify: backend `uv run python -m py_compile <file>` or `uv run pytest tests/test_router_jev.py -v -s` from `src/backend` (live router cases need `OPENROUTER_API_KEY`, skipped without it; costs fractions of a cent); frontend `npm run build` (`vue-tsc -b` typechecks — fix type errors before finishing).

## Backend (`src/backend/app`)

- `main.py`: `load_dotenv(override=True)`, one shared graph at startup via `load_mcp_tools()` + `build_graph()`. CORS defaults to `:5173` + `:8080`.
- Graph (`agents/graph.py`): `extract_requirements → router → {destination_research → wait_for_decision, orchestrator → subagents → main_llm}`. `thread_id = conversation_id`. Destination pick pauses via `interrupt()`/`resume` — every invoke needs the right `thread_id`. Only subagents with working tools are registered.
- LLMs (`agents/ai_models/llm.py`): main + `low_reasoning_llm` (minimal effort) are `z-ai/glm-5.3-flash` pinned to providers `together,baseten,fireworks,deepinfra,relace` — no fallback model, deliberate. `light_llm` is `google/gemma-3-12b-it` with fallbacks (`LIGHT_LLM_FALLBACKS`, default `gemma-3-27b-it,glm-5.3-flash`). `ResilientChatOpenRouter` retries once on 429 then rotates; non-429 errors propagate. Missing key fails fast at startup.
- Router (`agents/nodes/router.py`): Jev decision model (`typesafe/jev-1.13`, confidence ≥ 0.6) first, structured `light_llm` fallback, degrades to `main_llm`. Saved-choices confirmations skip routing entirely.
- MCP (`agents/mcp/client.py` owns `MCP_SERVERS`): `trvl` (stdio, needs `trvl` CLI) exposes a **single `travel` router tool** (`query`/`intent`/`params`) — `search_flights` etc. are intent values, not tools. TicketLens keeps only `search_pois`, `search_tours`, `get_tour`; weather keeps a 7-tool subset (`WEATHER_TOOL_NAMES`); rental-cars `search` is renamed `search_rental_cars`.
- Resilience by design: `load_mcp_tools()` skips unreachable servers; `_guard_tool` turns tool exceptions into text so subagents report gaps instead of killing the SSE stream. If a research agent is missing, check the `MCP tools ready` startup line.
- SSE (`api/v1/streaming.py`): events `status`, `token` (main_llm only), `requirements.updated`, `options` (per category), `plan.updated`, `agents.start`, `agent.done`, `agent.result`, `research.update`, `message` (destinations ride as `kind: "destinations"` cards), `stats` (tokens + OpenRouter `cost_usd` + duration), `title.updated`, `done`, `error`.
- Persistence (SQLite, `database/`): app data `data/app.db` (`DATABASE_URL`) + graph checkpoints `data/checkpoints.db` (`CHECKPOINT_DB_URL`); `*.db*` gitignored. Endpoints: `GET/POST /conversations`, `GET .../messages`, `GET .../state` (rehydrate panels after reload), `PATCH/DELETE .../{id}` (+ deterministic `POST .../choices`). `_stream` persists user turn up-front, assistant turn at end (write-through).
- `evals/dataset.jsonl` is prompt fixtures only — no eval runner exists.

## Human-in-the-loop protocol (do not break)

- Destination pick: frontend resumes with `"Let's go with <name>"` (`CHOOSE_PREFIX` in `agents/nodes/destinations.py`); anything else re-enters extract→research.
- Choice save: `POST /choices` resolves option ids against `available_options` and snapshots label/price into `trip_plan` (no LLM), then the frontend sends `"I'll go with: ..."` (`SAVED_CHOICES_PREFIX` in `agents/tools/plan.py`), which short-circuits `extract` + `router` straight to `main_llm`. Single-choice categories (`SINGLE_CHOICE_CATEGORIES` in `state.py`: `transportation`, `accommodation`, `rental_car`) replace per `(category, group)`; `activities` accumulates. New searches republish `available_options` per group but never touch `trip_plan`.

## Frontend (`src/frontend/src`)

- Chat state in `stores/travel.ts` (+ `travelEvents.ts`, `library.ts`, `ui.ts`), API in `api/travelService.ts` (+ `stream.ts`, `client.ts`), SSE types in `types/index.ts`, routes in `router/`.
- Markdown via `marked` + `DOMPurify` (`components/chat/richtext.ts`, also hosts price/group label helpers).
- Budget display: symbol + thousands separators (`€1,000`); total = per_person × travelers; `overBudget` flag drives the bar.
- Accent is a runtime selector (`theme/accents.ts`, default `sunset` `#ea580c`) overriding `--p-primary-*` vars — keep using the vars so dark mode and switching keep working.

## Conventions

- Commits: conventional + scope, e.g. `feat(phase-8): ...`, `docs: ...`, `refactor(api): ...`, `fix(frontend review): ...`.
- Backend modules carry Google-style docstrings + explanatory headers; match existing style when adding modules.
- Full graph/node reference: `docs/architecture.md`.
