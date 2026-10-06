"""Trip-plan tools: publish options and apply deterministic plan edits.

Choice saves via POST /choices bypass the LLM entirely and reuse the
same single-choice/group rules (`is_ui_choices_confirmation`).
"""
import json
from langchain.tools import tool, ToolRuntime
from langchain_core.messages import HumanMessage, ToolMessage
from langgraph.types import Command
from app.agents.state import PlanItem, PlanOption, SINGLE_CHOICE_CATEGORIES, get_field, _norm_group

# First line of the user message for UI button saves (POST /choices +
# normal send, like "Let's go with…"). extract + router short-circuit on
# it so the turn goes straight to main_llm with no extra LLM calls.
SAVED_CHOICES_PREFIX = "I'll go with:"


def is_ui_choices_confirmation(messages) -> bool:
    """True when the latest message confirms UI button choices.

    After a subagent search the user picks one or more options with the
    UI buttons. The frontend already saved them deterministically via
    POST /choices (see trip_plan in tools/plan.py) and then sends this
    machine-generated message ("I'll go with: ...") through the normal
    pipeline so the assistant acknowledges them.

    extract + router short-circuit on it straight to main_llm: there is
    nothing new to extract (the plan is already updated, an extraction
    LLM call would be wasted) and nothing to route (the destination is
    settled, so the Jev + router LLM calls would only conclude main_llm).
    main_llm then replies using the saved plan.

    Args:
        messages: the conversation message list (only the last matters).

    Returns:
        True when the latest message is a UI-choices confirmation.
    """
    return bool(
        messages
        and isinstance(messages[-1], HumanMessage)
        and str(messages[-1].content or "").startswith(SAVED_CHOICES_PREFIX)
    )


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

    Args:
        items: plan items (models or dicts) with price/currency.
        travelers: traveler count used to scale per-person prices.

    Returns:
        A (total, currency) tuple; currency is None when no priced item
        carries one.
    """
    total = 0.0
    currencies: dict[str, int] = {}
    for it in items or []:
        price = get_field(it, "price")
        if price is None:
            continue
        try:
            amount = float(price)
        except (TypeError, ValueError):
            continue
        if get_field(it, "per_person") and travelers:
            try:
                amount *= int(travelers)
            except (TypeError, ValueError):
                pass
        total += amount
        code = (get_field(it, "currency") or "").strip().upper() or "?"
        currencies[code] = currencies.get(code, 0) + 1
    currency = max(currencies, key=currencies.get) if currencies else None
    if currency == "?":
        currency = None
    return total, currency


@tool
def present_options(runtime: ToolRuntime, category: str, options: list[dict] | str | None, group: str = "") -> Command:
    """
    Publish the selectable options for one category (transportation,
    accommodation, activities, rental_car) so the UI can render choice
    controls and later choices resolve against this canonical list.

    WHEN TO CALL: after presenting research results in text, call once per
    category with the viable options (the same ones shown in prose, with
    stable ids like "t1", "h2"). When a category has distinct legs that
    the user must pick independently (outbound vs return, or leg 1 vs
    leg 2 of a multi-leg combo), call once PER LEG with group set to a
    short label ("outbound", "return", "leg 1"...); ids must stay unique
    within the category across legs ("t1".. for outbound, "r1".. for
    return). A later call for the same category AND group REPLACES that
    leg's list (new searches overwrite old options) without touching the
    other legs.

    options MUST be a list (JSON array) of option objects — never a dict
    keyed by id. Example: [{"id": "t1", "label": "...", "price": 110,
    "currency": "EUR", "per_person": false, "details": "..."}].

    Each option needs: id (short, unique within the category), label,
    price (number or null when unknown), currency (code like "EUR"),
    per_person (true when the price is per traveler), details (one-line
    extras: times, provider...). Preserve prices exactly as researched.
    """
    parsed = _normalize_options(options)
    if not parsed and options:
        # Non-empty input that normalized to nothing (e.g. a dict keyed
        # by id instead of a list): report an error so the LLM retries
        # with the right shape instead of silently publishing zero
        # options and leaving the UI without choice controls.
        return Command(
            update={
                "messages": [
                    ToolMessage(
                        content=(
                            f"Could not publish {category} options: expected a "
                            'non-empty LIST of option objects (e.g. [{"id": "t1", '
                            '"label": "...", "price": 110, ...}]), got '
                            f"{type(options).__name__}. Call again with a list."
                        ),
                        tool_call_id=runtime.tool_call_id,
                    )
                ],
            }
        )
    call_group = _norm_group(group)
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
                group=_norm_group(opt.get("group") or call_group),
            )
        )
    # Return only this category: the state reducer merges it with the
    # other categories (and, within a category, per group), so parallel
    # calls (one per category per turn) never overwrite each other.
    where = f"{category} [{call_group}]" if call_group else category
    return Command(
        update={
            "available_options": {category: canon},
            "messages": [
                ToolMessage(
                    content=f"Published {len(canon)} options for {where}.",
                    tool_call_id=runtime.tool_call_id,
                )
            ],
        }
    )


def _resolve_option(category: str, option_id: str | None, state) -> PlanOption | None:
    if not option_id:
        return None
    for opt in (state.get("available_options") or {}).get(category, []):
        if str(get_field(opt, "id")) == str(option_id):
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
    group: str = "",
) -> Command:
    """
    Save the user's choice into the trip plan.

    WHEN TO CALL: when the user picks an option by chat ("I'll take the
    morning flight", "the cheapest hotel"). Prefer option_id from the
    published options; only pass explicit label/price when the choice is
    not among them.

    Single-choice categories (transportation, accommodation, rental_car):
    a new choice REPLACES the previous one within the same group (e.g. a
    new "outbound" replaces the old "outbound" but keeps "return").
    Activities accumulate (same option_id twice is ignored). Prices
    snapshot at save time.
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
            group=_norm_group(resolved.group),
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
            group=_norm_group(group),
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
    key = lambda it: (
        as_dict(it).get("category"),
        _norm_group(as_dict(it).get("group")),
        str(as_dict(it).get("option_id")),
    )
    if category in SINGLE_CHOICE_CATEGORIES:
        plan = [it for it in plan if key(it)[:2] != (category, item.group)]
        plan.append(item)
        msg = f"Saved to trip plan: {item.label} ({category})."
    else:
        if any(key(it) == (category, item.group, item.option_id) for it in plan):
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
def remove_plan_item(runtime: ToolRuntime, category: str, option_id: str, group: str = "") -> Command:
    """
    Remove a choice from the trip plan.

    WHEN TO CALL: when the user unpicks something ("drop the city tour",
    "forget that hotel"). Match by category + option_id from the plan.
    Pass group too when the category has legs ("drop the return flight"):
    without it, every leg sharing that option_id is removed.
    """
    plan = list(runtime.state.get("trip_plan") or [])
    want_group = _norm_group(group)

    def matches(it) -> bool:
        d = it.model_dump() if isinstance(it, PlanItem) else dict(it)
        if (d.get("category"), str(d.get("option_id"))) != (category, str(option_id)):
            return False
        # Without group: legacy behavior (any leg with that id goes).
        return not want_group or _norm_group(d.get("group")) == want_group

    before = len(plan)
    kept = [it for it in plan if not matches(it)]
    msg = (
        "Removed from trip plan."
        if len(kept) < before
        else f"Nothing to remove: '{option_id}' is not in the {category} plan."
    )
    return Command(
        update={
            "trip_plan": kept,
            "messages": [ToolMessage(content=msg, tool_call_id=runtime.tool_call_id)],
        }
    )
