"""SSE streaming of a graph turn (`stream_turn`) plus its framing helpers.

Owns the wire protocol (event frames), per-node -> event translation,
turn persistence and turn usage stats. Payload shaping lives in
`presenters`; HTTP route registration lives in `conversations` / `plans`.
"""

import json
import logging
import time
import uuid
from datetime import datetime, timezone

from langchain_core.messages import HumanMessage
from langgraph.types import Command

from app.api.v1.presenters import (
    DESTINATIONS_INTRO_TEXT,
    candidate_to_card,
    option_to_dict,
    plan_payload,
    requirements_to_items,
    subagent_result_text,
)
from app.api.v1.titles import DEFAULT_CONVERSATION_TITLE, generate_title, has_title_context
from app.agents.usage import sum_entries, sum_turn_usage
from app.database.database import AsyncSessionLocal
from app.database import repositories as repo

logger = logging.getLogger("uvicorn.error")

STATUS_BY_ROUTE = {
    "destination_research": "Researching destinations…",
    "orchestrator": "Planning research…",
    "main_llm": "Writing answer…",
}

RESEARCH_KEY_BY_AGENT = {
    "weather_agent": "weather",
    "accommodation_agent": "accommodation",
    "transportation_agent": "transportation",
    "activities_agent": "activities",
    "rental_cars_agent": "rentalCar",
}


def frame(event: str, payload: dict) -> str:
    """One SSE frame for the wire protocol.

    Args:
        event: SSE event name (matches the frontend `TravelStreamEvent` map).
        payload: JSON-serializable event data.

    Returns:
        The raw `event: ...\\ndata: ...\\n\\n` frame string.
    """
    return f"event: {event}\ndata: {json.dumps(payload)}\n\n"


def trace_config(conversation_id: str) -> dict:
    """LangGraph invoke config with LangSmith trace context.

    `configurable.thread_id` is the checkpointer key (functional, not a
    filter). `metadata.conversation_id` is what makes runs filterable in
    the LangSmith UI; `tags` allow cross-cutting slices.

    Args:
        conversation_id: the conversation id, used as LangGraph thread id.

    Returns:
        The LangGraph invoke config for the turn.
    """
    return {
        "configurable": {"thread_id": conversation_id},
        "metadata": {"conversation_id": conversation_id},
        "tags": ["travel-planner"],
    }


def _task_agent(task) -> str | None:
    if hasattr(task, "agent"):
        return task.agent
    if isinstance(task, dict):
        return task.get("agent")
    return None


async def stream_turn(graph, conversation_id: str, message: str):
    """Run one graph turn and stream it as SSE frames.

    Translates per-node updates into frontend events, persists the user
    turn up-front and the assistant turn at the end (write-through), and
    folds auto-titling + turn usage stats into the stream. A 429 anywhere
    in the turn surfaces as a friendly `error` event instead of a crash.

    Args:
        graph: the compiled LangGraph app (shared at startup).
        conversation_id: the conversation id (LangGraph thread id).
        message: the user's message text (or resume value after interrupt).

    Yields:
        Raw SSE frame strings, ending with a `done` frame.
    """
    config = trace_config(conversation_id)
    # 1. Persist the user turn up-front so history survives mid-stream
    # crashes, then resume the interrupted turn or start a new one below.
    try:
        async with AsyncSessionLocal() as session:
            await repo.ensure_conversation(session, conversation_id)
            await repo.add_message(session, conversation_id, "user", "text", message)
            await session.commit()
    except Exception:
        logger.warning("Persist user turn failed for %s", conversation_id, exc_info=True)
    assistant_texts: list[str] = []
    assistant_cards: list[dict] = []
    agent_results: dict[str, str] = {}
    title_event: dict | None = None
    t0 = time.monotonic()
    try:
        state = await graph.aget_state(config)
        # Message/usage counts before the turn: only entries appended after
        # these indexes belong to this turn's stats.
        prev_len = len((state.values or {}).get("messages") or [])
        prev_usage_len = len((state.values or {}).get("turn_usage") or [])
        if state.interrupts:
            stream_input = Command(resume=message)
        else:
            yield frame("status", {"text": "Understanding your request…"})
            stream_input = {"messages": [HumanMessage(content=message)]}
        # Set after a main_tools update: the next main_llm tokens start a
        # new reply but stream into the same bubble, so separate them
        # with a blank line (markdown collapses extras, harmless).
        tools_ran = False
        # 2. Translate node updates into frontend SSE events.
        async for mode, payload in graph.astream(
            stream_input, config=config, stream_mode=["updates", "messages"]
        ):
            # Branch: token chunks stream text; node updates translate to events.
            if mode == "messages":
                chunk, metadata = payload
                if metadata.get("langgraph_node") != "main_llm":
                    continue
                content = getattr(chunk, "content", "")
                if isinstance(content, str) and content:
                    if tools_ran:
                        content = "\n\n" + content.lstrip("\n")
                        tools_ran = False
                    assistant_texts.append(content)
                    yield frame("token", {"text": content})
            elif mode == "updates":
                if not isinstance(payload, dict):
                    continue
                for node, output in payload.items():
                    if isinstance(output, list):
                        # Parallel tool calls (e.g. one present_options per
                        # category) stream as one update dict per call, not
                        # a single dict: merge them so every category still
                        # emits its event below.
                        merged: dict = {}
                        for item in output:
                            if not isinstance(item, dict):
                                continue
                            for k, v in item.items():
                                if (
                                    k == "available_options"
                                    and isinstance(v, dict)
                                    and isinstance(merged.get(k), dict)
                                ):
                                    merged[k] = {**merged[k], **v}
                                elif k not in merged:
                                    merged[k] = v
                        output = merged
                    if not isinstance(output, dict):
                        continue
                    if node == "extract_requirements" and output.get("requirements") is not None:
                        yield frame(
                            "requirements.updated",
                            {"requirements": requirements_to_items(output["requirements"])},
                        )
                    elif node == "router" and output.get("next_step"):
                        status = STATUS_BY_ROUTE.get(output["next_step"])
                        if status:
                            yield frame("status", {"text": status})
                    elif node == "destination_research" and output.get("destination_candidates"):
                        candidates = output["destination_candidates"]
                        cards = [candidate_to_card(c, i) for i, c in enumerate(candidates)]
                        assistant_cards.append({"destinations": cards})
                        yield frame(
                            "message",
                            {
                                "message": {
                                    "id": f"m{uuid.uuid4().hex[:8]}",
                                    "role": "assistant",
                                    "kind": "destinations",
                                    "text": DESTINATIONS_INTRO_TEXT,
                                    "destinations": cards,
                                    "createdAt": datetime.now(timezone.utc).isoformat(),
                                }
                            },
                        )
                    elif node == "orchestrator":
                        agents = [a for a in (_task_agent(t) for t in output.get("orchestration_plan", [])) if a]
                        if agents:
                            yield frame("status", {"text": "Executing specialized subagents…"})
                            yield frame("agents.start", {"agents": agents})
                    if node == "main_tools":
                        # The LLM paused mid-reply to run a tool: keep the
                        # status fresh so the UI can show activity during
                        # the gap between token batches.
                        yield frame("status", {"text": "Working on details…"})
                    if node == "main_tools" and output.get("requirements") is not None:
                        # Push requirements live instead of waiting for the turn (`see agents/tools/requirements.py`).
                        tools_ran = True
                        yield frame(
                            "requirements.updated",
                            {"requirements": requirements_to_items(output["requirements"])},
                        )
                    if node == "main_tools" and output.get("available_options") is not None:
                        # Push each touched category for choice controls (`see agents/tools/plan.py`).
                        # Re-read lists from state, not the payload: parallel same-category
                        # calls stream as separate updates that the merge above would collapse.
                        tools_ran = True
                        state_now = await graph.aget_state(config)
                        fresh_opts = (state_now.values or {}).get("available_options") or {}
                        for category in (output["available_options"] or {}):
                            opts = fresh_opts.get(category) or []
                            yield frame(
                                "options",
                                {
                                    "category": category,
                                    "options": [option_to_dict(o) for o in (opts or [])],
                                },
                            )
                    if node == "main_tools" and output.get("trip_plan") is not None:
                        # Push plan items + deterministic total live after plan edits.
                        tools_ran = True
                        state_now = await graph.aget_state(config)
                        yield frame("plan.updated", plan_payload(state_now.values or {}))
                    elif node in RESEARCH_KEY_BY_AGENT:
                        yield frame("agent.done", {"id": node})
                        yield frame(
                            "research.update",
                            {"key": RESEARCH_KEY_BY_AGENT[node], "state": "done"},
                        )
                        result_text = subagent_result_text(output)
                        if result_text:
                            agent_results[node] = result_text
                            yield frame("agent.result", {"id": node, "text": result_text})
        # 3. Fold auto-title + usage into stats, then persist the assistant turn.
        final = await graph.aget_state(config)
        # Aggregate the turn's `turn_usage` slice with `sum_entries` (`see agents/usage.py`, `see agents/state.py`).
        # Best-effort: stats stays None when nothing measurable happened.
        stats: dict | None = None
        try:
            values = final.values or {}
            entries = list(values.get("turn_usage") or [])[prev_usage_len:]
            # Auto-title once (default title + enough context only; manual
            # renames are never overwritten). Runs before stats so its
            # spend folds into the turn total.
            try:
                async with AsyncSessionLocal() as session:
                    conv = await repo.ensure_conversation(session, conversation_id)
                    if conv.title == DEFAULT_CONVERSATION_TITLE:
                        req = values.get("requirements")
                        cands = values.get("destination_candidates") or []
                        if has_title_context(message, req, cands):
                            new_title, title_usage = await generate_title(message, req, cands)
                            if title_usage is not None:
                                entries.append(title_usage)
                            if new_title:
                                conv.title = new_title[:60]
                                title_event = {"conversationId": conversation_id, "title": conv.title}
                    await session.commit()
            except Exception:
                title_event = None
            if not entries:
                # No node reported usage: fall back to message-carried usage
                # (a turn with zero LLM calls simply yields no stats).
                all_msgs = values.get("messages") or []
                usage = sum_turn_usage(list(all_msgs)[prev_len:])
            else:
                usage = sum_entries(entries)
            cost = usage.get("cost_usd")
            if usage.get("total_tokens") or usage.get("model") or cost is not None:
                stats = {
                    "duration_s": round(time.monotonic() - t0, 1),
                    "input_tokens": usage.get("input_tokens", 0),
                    "output_tokens": usage.get("output_tokens", 0),
                    "total_tokens": usage.get("total_tokens", 0),
                    "cost_usd": cost,
                    "model": usage.get("model"),
                }
        except Exception:
            stats = None
        req = (final.values or {}).get("requirements")
        if req is not None:
            yield frame("requirements.updated", {"requirements": requirements_to_items(req)})
        if (final.values or {}).get("trip_plan"):
            yield frame("plan.updated", plan_payload(final.values or {}))
        interrupt_texts: list[str] = []
        for interrupt in final.interrupts or []:
            if isinstance(interrupt.value, str) and interrupt.value:
                interrupt_texts.append(interrupt.value)
                yield frame(
                    "message",
                    {
                        "message": {
                            "id": f"m{uuid.uuid4().hex[:8]}",
                            "role": "assistant",
                            "kind": "text",
                            "text": interrupt.value,
                            "createdAt": datetime.now(timezone.utc).isoformat(),
                            **({"stats": stats} if stats else {}),
                        }
                    },
                )
        if stats:
            yield frame("stats", {"stats": stats})
        # Persist the assistant turn (text + destination cards + interrupts).
        # Subagent outputs ride along in the payload for exact rehydrate (`see api/v1/presenters.py`).
        try:
            async with AsyncSessionLocal() as session:
                await repo.ensure_conversation(session, conversation_id)
                results = [{"id": nid, "text": text} for nid, text in agent_results.items()]
                full_text = "".join(assistant_texts).strip()

                def _payload(extra: dict | None = None) -> dict | None:
                    base: dict = {}
                    if results:
                        base["subagentResults"] = results
                    if stats:
                        base["stats"] = stats
                    if extra:
                        base.update(extra)
                    return base or None

                if full_text:
                    await repo.add_message(
                        session, conversation_id, "assistant", "text", full_text,
                        _payload(),
                    )
                elif results or stats:
                    await repo.add_message(
                        session, conversation_id, "assistant", "text", "",
                        _payload(),
                    )
                for card in assistant_cards:
                    await repo.add_message(
                        session, conversation_id, "assistant", "destinations",
                        DESTINATIONS_INTRO_TEXT,
                        _payload(card),
                    )
                for text in interrupt_texts:
                    await repo.add_message(
                        session, conversation_id, "assistant", "text", text, _payload()
                    )
                # The auto-title above is already folded into stats; apply it
                # here unless someone renamed the conversation in between.
                if title_event is not None:
                    conv = await repo.ensure_conversation(session, conversation_id)
                    if conv.title == DEFAULT_CONVERSATION_TITLE or conv.title == title_event["title"]:
                        conv.title = title_event["title"][:60]
                await session.commit()
        except Exception:
            logger.warning("Persist assistant turn failed for %s", conversation_id, exc_info=True)
        if title_event is not None:
            yield frame("title.updated", title_event)
        yield "event: done\ndata: {}\n\n"
    except Exception as exc:
        if getattr(exc, "status_code", None) == 429 or "429" in str(exc):
            yield frame(
                "error",
                {"message": "All models are busy right now, please retry in a minute."},
            )
        else:
            yield frame("error", {"message": str(exc)})
