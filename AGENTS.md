# AGENTS.md

Notebook-driven prototype. No `src/`, `tests/`, CI, lint, or typecheck yet. All logic lives in `notebooks/phase1.ipynb` … `phase5.ipynb`. Target layout (`src/backend`, `src/frontend`, `mcp/`, `tests/`, `evaluation/`) in `README.md` does not exist — do not assume it.

## Source of truth

- `docs/architecture.md` + `README.md` (phases 1–5 done, 6–10 pending) for intent.
- Notebooks for verified behavior. Docs conflict with code on MCPs — trust the notebooks (below).

## Setup

- Python `==3.12.*` via `uv` (`pyproject.toml`, `uv.lock` committed, `.venv/` gitignored). Use `uv sync` / `uv run …`.
- Env is loaded in every notebook with `load_dotenv(override=True)`. Required keys: `OPENROUTER_API_KEY`, plus `LANGSMITH_*` for tracing. `.env` is gitignored — never commit it, never create `src/` config that bypasses it.
- LLMs go through OpenRouter (`base_url="https://openrouter.ai/api/v1"`, `ChatOpenAI` or `ChatOpenRouter`). Defaults: main `xiaomi/mimo-v2.5`, cheap/light `google/gemma-3-12b-it`.

## MCP endpoints (verified in phase5)

```python
MultiServerMCPClient({
  "ticketlens": {"transport": "http", "url": "https://mcp.ticketlens.com/"},
  "weather": {"transport": "streamable_http", "url": "https://open-meteo.caseyjhand.com/mcp"},
  "trvl": {"transport": "stdio", "command": "trvl", "args": ["mcp"]},  # requires `trvl` CLI installed
  "octotrip-rental-cars": {"transport": "http", "url": "https://mcp.octotrip.app/rental-cars/mcp"},
})
```

- `trvl` exposes a single `travel` router tool (`query` / `intent` / `params`); `search_flights`, `search_hotels`, etc. are `intent` values, not separate tools.
- Only `search_pois`, `search_tours`, `get_tour` are kept from TicketLens.

## Gotchas

- Windows + Jupyter + MCP stdio: Jupyter's stderr is not a real file and the MCP SDK fails to launch servers. Notebooks redirect the server's stderr to `DEVNULL` — keep that workaround for any new stdio MCP on Windows. Not needed on macOS/Linux.
- Checkpointing is `InMemorySaver` + `graph.compile(checkpointer=…)`; every `ainvoke` needs a `thread_id`. State classes (`TravelRequirements`, `DestinationCandidate`, `AgentTask`) are defined in `__main__`, which triggers LangGraph "deserializing unregistered type" msgpack warnings — expected until code moves to an importable package.
- No test command exists. Verify by re-running the touched notebook cells, not `pytest`.
