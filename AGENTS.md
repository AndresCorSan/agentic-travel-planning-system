# AGENTS.md

Monorepo: `src/backend` (FastAPI + LangGraph) + `src/frontend` (Vue 3 + PrimeVue + Pinia). `notebooks/` is the legacy phase 1–5 prototype — `src/` is the source of truth now. `src/backend/tests/` is empty; no test runner, CI, or lint exists.

## Run

- Backend (from `src/backend`, so `app.*` imports resolve): `uv run uvicorn app.main:app --port 8000`. Restart it for any change under `app/` (no reload configured).
- Frontend (from `src/frontend`): `npm run dev` (port 5173). Backend CORS allows only `http://localhost:5173`.
- Frontend env (`src/frontend/.env`): `VITE_API_BASE_URL=http://localhost:8000/api/v1`.
- Verify backend with `uv run python -m py_compile <file>`; verify frontend with `npm run build` (`vue-tsc -b` typechecks — fix type errors before finishing).
- Windows shell is PowerShell 5.1: no `&&`, no `head`; use `;` / `Select-Object`.

## Backend (`src/backend/app`)

- `main.py`: `load_dotenv(override=True)`, builds one shared graph at startup via `load_mcp_tools()` + `build_graph()`. Required env: `OPENROUTER_API_KEY` (root `.env`). Optional: `LIGHT_LLM_FALLBACKS`, `LANGSMITH_*`.
- Graph (`agents/graph.py`): `extract_requirements → router → {destination_research → wait_for_decision, orchestrator → subagents → main_llm}`. Checkpointer is `AsyncSqliteSaver` (`data/checkpoints.db`), `thread_id = conversation_id`. Destination choice uses `interrupt()`/`resume` — every `ainvoke` needs the right `thread_id`.
- LLMs (`agents/llm.py`): main + subagents use `xiaomi/mimo-v2.5` (Xiaomi provider, no fallback model — deliberate); `light_llm` is `google/gemma-3-12b-it` with fallbacks. `ResilientChatOpenRouter` retries once on 429 then rotates models; non-429 errors propagate.
- MCP (`agents/mcp/client.py` owns `MCP_SERVERS`): `trvl` (stdio, needs `trvl` CLI) exposes a **single `travel` router tool** (`query`/`intent`/`params`) — `search_flights` etc. are intent values, not tools. TicketLens keeps only `search_pois`, `search_tours`, `get_tour`; rental-cars `search` is renamed `search_rental_cars`.
- Resilience by design: `load_mcp_tools()` skips unreachable servers and the graph builds with whatever tools exist — if a research agent is missing at runtime, check the startup log line `MCP tools ready`. `_guard_tool` turns tool exceptions into text so subagents report gaps instead of killing the SSE stream.
- SSE (`api/v1/conversations.py`): events `status`, `agents.start`, `agent.done`, `agent.result`, `research.update`, `requirements.updated`, `options`, `plan.updated`, `token` (main_llm only), `message`, `done`, `error`.
- Persistence (phase 9, SQLite): `database/` owns `database.py` (engine/`DATABASE_URL`, default `data/app.db`), `models.py` (`conversations`, `messages`), `repositories.py`, `checkpointer.py` (`AsyncSqliteSaver`, `data/checkpoints.db` via `CHECKPOINT_DB_URL`). `*.db*` gitignored. CRUD: `GET/POST /conversations`, `GET .../messages`, `GET .../state` (rehydrate), `PATCH/DELETE .../{id}`. `_stream` persists user + assistant turns write-through; sidebar list/rename/delete are optimistic + fire-and-forget.

## Human-in-the-loop protocol (do not break)

- Destination pick: frontend sends `"Let's go with <name>"` (`CHOOSE_PREFIX` in `agents/nodes/destinations.py`); anything else re-enters extract→research.
- Choice save: `POST /choices` persists deterministically (`tools/plan.py`), then the frontend sends a normal message starting `"I'll go with:\n- Category: label"` (`SAVED_CHOICES_PREFIX`), which short-circuits `extract` + `router` straight to `main_llm`. Multi same-category joined with `, `; single-choice categories (`SINGLE_CHOICE_CATEGORIES` in `state.py`) replace, `activities` accumulates. New searches overwrite `available_options` but never touch `trip_plan`.
- `POST /choices` returns `{saved, plan}`; frontend `applyPlan()` handles both it and `plan.updated` events.
- Deliberately discarded (see `docs/architecture.md`): LLM critic / planner→critic→replan loop — the user choosing from priced options already covers it. Do not reintroduce without discussion.

## Frontend (`src/frontend/src`)

- Markdown via `marked` + `DOMPurify` (`components/chat/richtext.ts`); chat state in `stores/travel.ts`, API in `api/travelService.ts`, SSE types in `types/index.ts`.
- Budget display: symbol + thousands separators (`€1,000`); total = per_person × travelers; `overBudget` flag drives the bar.
- Accent color sunset `#ea580c` — use `var(--p-primary-600)` / `color-mix()` so dark mode keeps working.

## Conventions

- Commits: conventional + phase scope, e.g. `feat(phase-8): ...`, `docs: ...`, `style(phase-8): ...`.
- Never commit `.env` (root or frontend); never create config that bypasses root `.env`.
