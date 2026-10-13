/*
 * Backend-event translator for one travel turn: converts the SSE StreamEvents
 * from the graph (tokens, status, options, plan updates, ...) into travel
 * store mutations. Owns the per-turn buffers (pending subagent results,
 * pending option blocks, stream id counter); the travel store drives it via
 * resetTurn() at turn start and applyEvent() per event, and keeps the thread
 * state (messages, requirements, plan) for itself.
 */
import type { Ref } from 'vue';
import { AGENT_LABELS, AGENT_RESEARCH_KEY } from '../api/stream';
import type { AgentRow, ChatMessage, PlanOption, PlanUpdate, ResearchStatus, RequirementItem, StreamEvent, SubagentResult } from '../types';
import { useLibraryStore } from './library';

export interface EventApplierDeps {
  streamStatus: Ref<string>;
  agentRows: Ref<AgentRow[]>;
  streaming: Ref<ChatMessage | null>;
  research: Ref<ResearchStatus>;
  requirements: Ref<RequirementItem[]>;
  optionsByCategory: Ref<Record<string, PlanOption[]>>;
  optionsByMessage: Ref<Record<string, { category: string; options: PlanOption[] }[]>>;
  cache: Ref<Record<string, ChatMessage>>;
  messageIds: Ref<string[]>;
  applyPlan: (p: PlanUpdate) => void;
  mergeOptions: (existing: PlanOption[], incoming: PlanOption[]) => PlanOption[];
}

export function createEventApplier(deps: EventApplierDeps) {
  // Specialist outputs buffered during the current turn (`agent.result`
  // events); attached to the assistant message when it is finalized.
  let pendingResults: SubagentResult[] = [];
  // Options published during the current turn (`options` events). If the
  // finalized message carries no [[option:id]] flags (the LLM skipped
  // them), these render as an automatic block under that message instead
  // of losing the choice controls for the turn.
  let pendingTurnOptions: { category: string; options: PlanOption[] }[] = [];
  let streamCounter = 1000;

  function resetTurn() {
    pendingResults = [];
    pendingTurnOptions = [];
  }

  function attachPendingOptions(messageId: string) {
    if (!pendingTurnOptions.length) return;
    deps.optionsByMessage.value = { ...deps.optionsByMessage.value, [messageId]: pendingTurnOptions };
    pendingTurnOptions = [];
  }

  function applyEvent(ev: StreamEvent) {
    switch (ev.type) {
      // Live progress text from the backend.
      case 'status':
        deps.streamStatus.value = ev.text;
        break;
      // Mark research active and build the live status rows.
      case 'agents.start':
        for (const id of ev.agents) {
          const key = AGENT_RESEARCH_KEY[id];
          if (key) deps.research.value[key] = 'active';
          const row = deps.agentRows.value.find((r) => r.id === id);
          if (row) row.state = 'active';
          else deps.agentRows.value.push({ id, label: AGENT_LABELS[id] ?? id, state: 'active' });
        }
        break;
      // Close the status row and its research key.
      case 'agent.done': {
        const row = deps.agentRows.value.find((r) => r.id === ev.id);
        if (row) row.state = 'done';
        const key = AGENT_RESEARCH_KEY[ev.id];
        if (key) deps.research.value[key] = 'done';
        break;
      }
      // Buffer specialist output for the finalized message.
      case 'agent.result': {
        if (!pendingResults.some((r) => r.id === ev.id)) {
          pendingResults.push({ id: ev.id, label: AGENT_LABELS[ev.id] ?? ev.id, text: ev.text });
        }
        // Show the accordion live under the streaming bubble as well.
        if (deps.streaming.value) {
          deps.streaming.value = { ...deps.streaming.value, subagentResults: [...pendingResults] };
        }
        break;
      }
      // Backend-owned research state for the side panel.
      case 'research.update':
        deps.research.value[ev.key] = ev.state;
        break;
      // Graph-owned requirements replace the panel list.
      case 'requirements.updated':
        deps.requirements.value = ev.requirements;
        break;
      // Merge per group; buffer a fallback block for the turn.
      case 'options':
        deps.optionsByCategory.value = { ...deps.optionsByCategory.value, [ev.category]: deps.mergeOptions(deps.optionsByCategory.value[ev.category] ?? [], ev.options) };
        pendingTurnOptions = [
          ...pendingTurnOptions.filter((g) => g.category !== ev.category),
          { category: ev.category, options: deps.mergeOptions(pendingTurnOptions.find((g) => g.category === ev.category)?.options ?? [], ev.options) },
        ];
        break;
      // Server-truth plan and totals.
      case 'plan.updated':
        deps.applyPlan(ev);
        break;
      // Tokens stream from main_llm only; see `streaming.stream_turn`.
      case 'token':
        if (!deps.streaming.value) {
          deps.streaming.value = {
            id: `s${++streamCounter}`,
            role: 'assistant',
            kind: 'text',
            text: '',
            // Results arrived before the first token: show the accordions
            // above the answer from the start instead of popping them in
            // at the end.
            ...(pendingResults.length ? { subagentResults: [...pendingResults] } : {}),
            createdAt: new Date().toISOString()
          };
        }
        deps.streaming.value = { ...deps.streaming.value, text: (deps.streaming.value.text ?? '') + ev.text };
        break;
      // Flush the streaming bubble, then store the finalized message.
      case 'message':
        if (deps.streaming.value) {
          if (pendingResults.length) {
            deps.streaming.value = { ...deps.streaming.value, subagentResults: [...pendingResults] };
          }
          deps.cache.value[deps.streaming.value.id] = deps.streaming.value;
          deps.messageIds.value.push(deps.streaming.value.id);
          if (ev.message.role !== 'assistant') attachPendingOptions(deps.streaming.value.id);
          deps.streaming.value = null;
          pendingResults = [];
        }
        deps.cache.value[ev.message.id] = ev.message;
        deps.messageIds.value.push(ev.message.id);
        if (ev.message.role === 'assistant') attachPendingOptions(ev.message.id);
        break;
      case 'stats': {
        // Turn usage (tokens/cost/duration): attach to the live bubble if
        // still streaming, else to the latest assistant message already
        // flushed to the cache (e.g. destination cards).
        if (deps.streaming.value) {
          deps.streaming.value = { ...deps.streaming.value, stats: ev.stats };
        } else {
          for (let i = deps.messageIds.value.length - 1; i >= 0; i--) {
            const m = deps.cache.value[deps.messageIds.value[i]];
            if (m?.role === 'assistant') {
              deps.cache.value[m.id] = { ...m, stats: ev.stats };
              break;
            }
          }
        }
        break;
      }
      // Optimistic sidebar rename; no refetch.
      case 'title.updated': {
        const library = useLibraryStore();
        const row = library.conversations.find((c) => c.id === ev.conversationId);
        if (row) {
          row.title = ev.title;
          row.updatedAt = 'just now';
        }
        break;
      }
      // Flush any open bubble; the turn had no final message.
      case 'done':
        if (deps.streaming.value) {
          if (pendingResults.length) {
            deps.streaming.value = { ...deps.streaming.value, subagentResults: [...pendingResults] };
          }
          deps.cache.value[deps.streaming.value.id] = deps.streaming.value;
          deps.messageIds.value.push(deps.streaming.value.id);
          attachPendingOptions(deps.streaming.value.id);
          deps.streaming.value = null;
          pendingResults = [];
        }
        break;
      // Throw to send(), which keeps the user text and shows a failure bubble.
      case 'error':
        deps.streaming.value = null;
        throw new Error(ev.message);
    }
  }

  return { applyEvent, resetTurn };
}
