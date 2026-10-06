"""Turn-level LLM usage stats (tokens + $ shown under each assistant message).

How it works, end to end:
1. Collect: each graph node reports one entry per LLM call into the
   `turn_usage` state channel (`state.py`) via `collect_usage` /
   `message_usage`. This also covers calls that leave no AIMessage
   behind (structured outputs, subagents).
2. Slice: the channel accumulates across turns, so `streaming.stream_turn`
   snapshots its length at turn start and only aggregates the new entries.
3. Sum: `sum_entries` adds that slice field by field (e.g. the entries'
   input_tokens add up to the displayed total) into the `stats` dict.

OpenRouter reports each response's cost inline (`response_metadata["cost"]`),
so no extra API calls are needed. Best-effort: entries without cost data
are skipped, and `cost_usd` None shows tokens without cost. Never raises.
"""
from __future__ import annotations

from langchain_core.messages import AIMessage


def _usage_of(msg) -> tuple[int, int]:
    """(input_tokens, output_tokens) for one chat message, else (0, 0)."""
    usage = getattr(msg, "usage_metadata", None)
    if isinstance(usage, dict):
        try:
            return int(usage.get("input_tokens") or 0), int(usage.get("output_tokens") or 0)
        except (TypeError, ValueError):
            return 0, 0
    return 0, 0


def sum_turn_usage(messages: list) -> dict:
    """Sum usage over the turn's new messages.

    Fallback used by `streaming.stream_turn` when no node reported to the
    `turn_usage` channel. Prefer `sum_entries` (also covers structured
    outputs and subagents, which leave no AIMessage behind).
    """
    return sum_entries(collect_usage(messages or [], "main_llm"))


def message_usage(msg, node: str) -> dict | None:
    """Usage entry for one AIMessage, or None when it carries nothing.

    Called by graph nodes (and `titles.generate_title`) to report each
    LLM call into the `turn_usage` channel. Entry shape (JSON-safe, so
    the checkpointer can persist it):
    {node, model, input_tokens, output_tokens, total_tokens, cost_usd}.
    """
    if not isinstance(msg, AIMessage):
        return None
    inp, out = _usage_of(msg)
    model: str | None = None
    cost: float | None = None
    meta = getattr(msg, "response_metadata", None)
    if isinstance(meta, dict):
        name = meta.get("model_name") or meta.get("model")
        if name:
            model = str(name)
        try:
            if meta.get("cost") is not None:
                cost = float(meta["cost"])
        except (TypeError, ValueError):
            cost = None
    if not (inp or out or cost is not None or model):
        return None
    return {
        "node": node,
        "model": model,
        "input_tokens": inp,
        "output_tokens": out,
        "total_tokens": inp + out,
        "cost_usd": cost,
    }


def collect_usage(messages: list, node: str) -> list[dict]:
    """One usage entry per AIMessage that carries usage data."""
    entries = []
    for msg in messages or []:
        entry = message_usage(msg, node)
        if entry is not None:
            entries.append(entry)
    return entries


def sum_entries(entries: list) -> dict:
    """Aggregate usage entries into one turn total.

    Called by `streaming.stream_turn` on the turn's slice of the
    `turn_usage` channel. Returns {input_tokens, output_tokens,
    total_tokens (= in + out), cost_usd (None when no entry carried one),
    model (last non-empty seen)}."""
    input_tokens = 0
    output_tokens = 0
    cost = 0.0
    has_cost = False
    model: str | None = None
    for e in entries or []:
        if not isinstance(e, dict):
            continue
        try:
            input_tokens += int(e.get("input_tokens") or 0)
            output_tokens += int(e.get("output_tokens") or 0)
        except (TypeError, ValueError):
            pass
        if e.get("cost_usd") is not None:
            try:
                cost += float(e["cost_usd"])
                has_cost = True
            except (TypeError, ValueError):
                pass
        if e.get("model"):
            model = str(e["model"])
    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": input_tokens + output_tokens,
        "model": model,
        "cost_usd": cost if has_cost else None,
    }
