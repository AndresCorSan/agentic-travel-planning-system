// Full markdown renderer for LLM replies: marked for parsing,
// DOMPurify for sanitizing (content comes from the LLM into v-html).
import DOMPurify from 'dompurify';
import { marked } from 'marked';
import type { PlanOption } from '../../types';

marked.setOptions({ breaks: true });

export const PRICE_SYMBOLS: Record<string, string> = { EUR: '€', USD: '$', GBP: '£', JPY: '¥' };

export function formatOptionPrice(o: Pick<PlanOption, 'price' | 'currency' | 'per_person'>): string {
  if (o.price === null || o.price === undefined) return '';
  const code = (o.currency || '').toUpperCase();
  const symbol = PRICE_SYMBOLS[code];
  const prefix = symbol ?? (code ? `${code} ` : '');
  const amount = Number.isInteger(o.price) ? o.price.toLocaleString() : o.price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  return `${prefix}${amount}${o.per_person ? ' pp' : ''}`;
}

export interface OptionRenderCtx {
  lookup: (id: string) => (PlanOption & { category: string }) | undefined;
  checked: (id: string) => boolean;
  locked: boolean;
  single: (category: string) => boolean;
}

function escapeHtml(s: string): string {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

export function categoryLabel(category: string): string {
  const words = category.replace(/_/g, ' ').trim();
  return words ? words.charAt(0).toUpperCase() + words.slice(1) : category;
}

/** Display label for an option group ("outbound" -> "Outbound"). */
export function groupLabel(group: string): string {
  const words = group.replace(/_/g, ' ').trim();
  return words ? words.charAt(0).toUpperCase() + words.slice(1) : group;
}

function renderControl(id: string, o: PlanOption & { category: string }, ctx: OptionRenderCtx): string {
  const price = formatOptionPrice(o);
  return `<button type="button" class="opt-pick" data-option="${escapeHtml(id)}" data-checked="${ctx.checked(id) ? '1' : '0'}" data-locked="${ctx.locked ? '1' : '0'}" data-single="${ctx.single(o.category) ? '1' : '0'}" title="${escapeHtml(o.details || o.label)}"><span class="opt-box"></span><span class="opt-label">${escapeHtml(o.label)}</span>${price ? `<span class="opt-price">${escapeHtml(price)}</span>` : ''}</button>`;
}

/** Plain markdown render (no option flags: choice controls always render
as the grouped block under the message via renderOptionGroups). */
export function renderRich(text: string): string {
  return DOMPurify.sanitize(marked.parse(text) as string);
}

export interface OptionGroup {
  category: string;
  options: PlanOption[];
}

/** Choice controls grouped by category, rendered under the message.
// Categories split further by option group, so legs like outbound vs
// return render as their own selector sections. Same data-option
// delegation as before; clicks are handled by the host component, so
// no Vue bindings are needed inside v-html. */
export function renderOptionGroups(groups: OptionGroup[], ctx: OptionRenderCtx): string {
  const parts: string[] = [];
  for (const g of groups) {
    const byGroup = new Map<string, PlanOption[]>();
    for (const o of g.options ?? []) {
      const k = o.group ?? '';
      if (!byGroup.has(k)) byGroup.set(k, []);
      byGroup.get(k)!.push(o);
    }
    for (const [group, opts] of byGroup) {
      const buttons = opts
        .map((o) => {
          const full = ctx.lookup(o.id) ?? { ...o, category: g.category };
          return renderControl(o.id, full, ctx);
        })
        .join('');
      if (!buttons) continue;
      const title = group ? `${categoryLabel(g.category)} — ${groupLabel(group)}` : categoryLabel(g.category);
      parts.push(
        `<div class="opt-group"><p class="opt-cat">${escapeHtml(title)}</p><div class="opt-list">${buttons}</div></div>`
      );
    }
  }
  if (!parts.length) return '';
  return DOMPurify.sanitize(`<div class="opt-fallback">${parts.join('')}</div>`);
}
