import json
from langchain.tools import tool, ToolRuntime
from langchain_core.messages import ToolMessage
from langgraph.types import Command
from app.agents.state import PlanItem, PlanOption, SINGLE_CHOICE_CATEGORIES

# First line of the user message for UI button saves (POST /choices +
# normal send, like "Let's go with…"). extract + router short-circuit on
# it so the turn goes straight to main_llm with no extra LLM calls.
SAVED_CHOICES_PREFIX = "I'll go with:"


def _normalize_options(value) -> list[dict]:
    """Accept a list of option dicts or a JSON-encoded string thereof."""
    if value is None:
        return []
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                value = parsed
            else:
                return []
        except json.JSONDecodeError:
            return []
    if not isinstance(value, list):
        return []
    return [v for v in value if isinstance(v, dict)]


def plan_total(items: list, travelers: int | None = None) -> tuple[float, str | None]:
    """Deterministic trip total: per-person prices × travelers, totals as-is.

    Items without a price are skipped. Currency is the most common one
    among priced items (no FX conversion — mixed currencies are reported
    per item in the payload).
    """
    total = 0.0
    currencies: dict[str, int] = {}
    for it in items or []:
        get = lambda name: getattr(it, name, None) if not isinstance(it, dict) else it.get(name)
        price = get("price")
        if price is None:
            continue
        try:
            amount = float(price)
        except (TypeError, ValueError):
            continue
        if get("per_person") and travelers:
            try:
                amount *= int(travelers)
            except (TypeError, ValueError):
                pass
        total += amount
        code = (get("currency") or "").strip().upper() or "?"
        currencies[code] = currencies.get(code, 0) + 1
    currency = max(currencies, key=currencies.get) if currencies else None
    if currency == "?":
        currency = None
    return total, currency


@tool
def present_options(runtime: ToolRuntime, category: str, options) -> Command:
    """
    Publish the selectable options for one category (transportation,
    accommodation, activities, rental_car) so the UI can render choice
    controls and later choices resolve against this canonical list.

    WHEN TO CALL: after presenting research results in text, call once per
    category with the viable options (the same ones shown in prose, with
    stable ids like "t1", "h2"). A later call for the same category
    REPLACES the previous list (new searches overwrite old options).

    Each option needs: id (short, unique within the category), label,
    price (number or null when unknown), currency (code like "EUR"),
    per_person (true when the price is per traveler), details (one-line
    extras: times, provider...). Preserve prices exactly as researched.
    """
    parsed = _normalize_options(options)
    canon: list[PlanOption] = []
    for i, opt in enumerate(parsed):
        oid = str(opt.get("id") or f"{category}-{i + 1}").strip()
        label = str(opt.get("label") or oid).strip()
        try:
            price = float(opt["price"]) if opt.get("price") is not None else None
        except (TypeError, ValueError):
            price = None
        canon.append(
            PlanOption(
                id=oid,
                label=label,
                price=price,
                currency=(str(opt.get("currency") or "").strip().upper() or None),
                per_person=bool(opt.get("per_person", False)),
                details=str(opt.get("details") or "").strip(),
            )
        )
    # Return only this category: the state reducer merges it with the
    # other categories, so parallel calls (one per category per turn)
    # never overwrite each other.
    return Command(
        update={
            "available_options": {category: canon},
            "messages": [
                ToolMessage(
                    content=f"Published {len(canon)} options for {category}.",
                    tool_call_id=runtime.tool_call_id,
                )
            ],
        }
    )


def _resolve_option(category: str, option_id: str | None, state) -> PlanOption | None:
    if not option_id:
        return None
    for opt in (state.get("available_options") or {}).get(category, []):
        get = lambda name: getattr(opt, name, None) if not isinstance(opt, dict) else opt.get(name)
        if str(get("id")) == str(option_id):
            return opt if isinstance(opt, PlanOption) else PlanOption(**opt)
    return None


@tool
def add_plan_item(
    runtime: ToolRuntime,
    category: str,
    option_id: str | None = None,
    label: str | None = None,
    price: float | None = None,
    currency: str | None = None,
    per_person: bool = False,
    details: str | None = None,
) -> Command:
    """
    Save the user's choice into the trip plan.

    WHEN TO CALL: when the user picks an option by chat ("I'll take the
    morning flight", "the cheapest hotel"). Prefer option_id from the
    published options; only pass explicit label/price when the choice is
    not among them.

    Single-choice categories (transportation, accommodation, rental_car):
    a new choice REPLACES the previous one. Activities accumulate (same
    option_id twice is ignored). Prices snapshot at save time.
    """
    state = runtime.state
    resolved = _resolve_option(category, option_id, state)
    if resolved is not None:
        item = PlanItem(
            category=category,
            option_id=resolved.id,
            label=resolved.label,
            price=resolved.price,
            currency=resolved.currency,
            per_person=resolved.per_person,
            details=resolved.details,
        )
    elif label:
        try:
            price_val = float(price) if price is not None else None
        except (TypeError, ValueError):
            price_val = None
        item = PlanItem(
            category=category,
            option_id=str(option_id or label),
            label=label,
            price=price_val,
            currency=(str(currency or "").strip().upper() or None),
            per_person=bool(per_person),
            details=str(details or "").strip(),
        )
    else:
        return Command(
            update={
                "messages": [
                    ToolMessage(
                        content=f"Could not save: option '{option_id}' is not among the published {category} options and no label was given. Ask the user to clarify.",
                        tool_call_id=runtime.tool_call_id,
                    )
                ],
            }
        )
    plan = list(state.get("trip_plan") or [])
    as_dict = lambda it: it.model_dump() if isinstance(it, PlanItem) else dict(it)
    if category in SINGLE_CHOICE_CATEGORIES:
        plan = [it for it in plan if as_dict(it).get("category") != category]
        plan.append(item)
        msg = f"Saved to trip plan: {item.label} ({category})."
    else:
        if any(as_dict(it).get("category") == category and as_dict(it).get("option_id") == item.option_id for it in plan):
            msg = f"Already in trip plan: {item.label}."
        else:
            plan.append(item)
            msg = f"Added to trip plan: {item.label} ({category})."
    return Command(
        update={
            "trip_plan": plan,
            "messages": [ToolMessage(content=msg, tool_call_id=runtime.tool_call_id)],
        }
    )


@tool
def remove_plan_item(runtime: ToolRuntime, category: str, option_id: str) -> Command:
    """
    Remove a choice from the trip plan.

    WHEN TO CALL: when the user unpicks something ("drop the city tour",
    "forget that hotel"). Match by category + option_id from the plan.
    """
    plan = list(runtime.state.get("trip_plan") or [])

    def key(it):
        d = it.model_dump() if isinstance(it, PlanItem) else dict(it)
        return d.get("category"), str(d.get("option_id"))

    kept = [it for it in plan if key(it) != (category, str(option_id))]
    msg = (
        "Removed from trip plan."
        if len(kept) < len(plan)
        else f"Nothing to remove: '{option_id}' is not in the {category} plan."
    )
    return Command(
        update={
            "trip_plan": kept,
            "messages": [ToolMessage(content=msg, tool_call_id=runtime.tool_call_id)],
        }
    )
