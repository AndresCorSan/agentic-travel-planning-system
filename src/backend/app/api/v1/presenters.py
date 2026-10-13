"""Pure state -> frontend-payload mappers for the API layer.

No FastAPI, no DB, no graph: only `agents.state` / `agents.tools.plan`
plus stdlib, so this module is unit-testable in isolation.
"""

from datetime import timezone
from functools import partial

from app.agents.state import get_field
from app.agents.tools.plan import plan_total

# Intro line for destination candidate cards. Sent live over SSE and
# persisted for rehydrate — one constant so reloads show the same text.
DESTINATIONS_INTRO_TEXT = "Here are my top picks — choose one or tell me what to adjust."

AGENT_RESULT_MAX_CHARS = 8000

CURRENCY_SYMBOLS = {"EUR": "€", "USD": "$", "GBP": "£", "JPY": "¥"}


def format_budget(budget, currency) -> str | None:
    """User-friendly budget label: symbol + thousands separator (€1,000).

    Unknown currency codes fall back to "CODE 1,000" (never glued).
    Returns None when there is no budget so the panel shows Not specified.

    Args:
        budget: numeric budget amount, if any.
        currency: ISO currency code (e.g. "EUR"), if any.

    Returns:
        The formatted label, or None when there is no budget.
    """
    if not budget:
        return None
    code = (currency or "").strip().upper()
    symbol = CURRENCY_SYMBOLS.get(code)
    prefix = symbol if symbol is not None else (f"{code} " if code else "")
    amount = f"{budget:,.0f}" if float(budget).is_integer() else f"{budget:,.2f}"
    return f"{prefix}{amount}"


def option_to_dict(opt) -> dict:
    return {
        "id": str(get_field(opt, "id", "")),
        "label": get_field(opt, "label", "") or "",
        "price": get_field(opt, "price"),
        "currency": get_field(opt, "currency"),
        "per_person": bool(get_field(opt, "per_person", False)),
        "details": get_field(opt, "details", "") or "",
        "group": str(get_field(opt, "group", "") or ""),
    }


def plan_payload(values: dict) -> dict:
    """Trip plan + deterministic total for the Plan panel / Budget.

    Args:
        values: graph state snapshot with `trip_plan` and `requirements`.

    Returns:
        Dict with the plan items plus the deterministic total, currency,
        budget and overBudget flag.
    """
    raw_plan = (values or {}).get("trip_plan") or []
    req = (values or {}).get("requirements")
    travelers = get_field(req, "travelers")
    budget = get_field(req, "budget")
    items = []
    for it in raw_plan:
        items.append({
            "category": get_field(it, "category"),
            "option_id": str(get_field(it, "option_id", "")),
            "label": get_field(it, "label", "") or "",
            "price": get_field(it, "price"),
            "currency": get_field(it, "currency"),
            "per_person": bool(get_field(it, "per_person", False)),
            "details": get_field(it, "details", "") or "",
            "group": str(get_field(it, "group", "") or ""),
        })
    total, currency = plan_total(raw_plan, travelers)
    return {
        "plan": items,
        "total": total,
        "currency": currency,
        "budget": budget,
        "overBudget": bool(budget and total > float(budget)),
    }


def candidate_to_card(candidate, index: int) -> dict:
    score = get_field(candidate, "score", 0) or 0
    code = (get_field(candidate, "country_code", "") or "").strip().lower()
    # Blank invalid codes so the UI hides the flag instead of requesting a broken URL.
    if len(code) != 2 or not code.isalpha():
        code = ""
    return {
        "id": f"dest-{index}",
        "name": get_field(candidate, "destination", "Unknown"),
        "country": get_field(candidate, "country", "") or "",
        "country_code": code,
        "tagline": get_field(candidate, "reason", "") or "",
        "highlights": get_field(candidate, "highlights", []) or [],
        "suitability": int(round(float(score) * 10)),
        "drawback": get_field(candidate, "drawback", "") or "",
    }


def requirements_to_items(req) -> list[dict]:
    """TravelRequirements -> RequirementItem[] for the Travel State panel.

    Args:
        req: a `TravelRequirements` model or plain dict (None allowed).

    Returns:
        The fixed 10-row RequirementItem list; empty when req is None.
    """
    if req is None:
        return []
    get = partial(get_field, req)
    destination = get("destination")
    origin = get("origin")
    travel_dates = get("travel_dates")
    duration_days = get("duration_days")
    travelers = get("travelers")
    budget = get("budget")
    currency = get("currency")
    transport_mode = get("transport_mode")
    accommodation_type = get("accommodation_type")
    interests = get("interests") or []
    constraints = get("constraints") or []
    return [
        {"key": "destination", "label": "Destination", "value": destination, "confirmed": bool(destination)},
        {"key": "origin", "label": "Origin", "value": origin, "confirmed": bool(origin)},
        {"key": "dates", "label": "Dates", "value": travel_dates, "confirmed": bool(travel_dates)},
        {
            "key": "duration",
            "label": "Duration",
            "value": f"{duration_days} days" if duration_days else None,
            "confirmed": bool(duration_days),
        },
        {
            "key": "travelers",
            "label": "Travelers",
            "value": str(travelers) if travelers else None,
            "confirmed": bool(travelers),
        },
        {
            "key": "budget",
            "label": "Budget",
            "value": format_budget(budget, currency),
            "confirmed": bool(budget),
        },
        {
            "key": "interests",
            "label": "Interests",
            "value": ", ".join(interests) if interests else None,
            "confirmed": bool(interests),
        },
        {
            "key": "transport",
            "label": "Transport",
            "value": transport_mode,
            "confirmed": bool(transport_mode),
        },
        {
            "key": "accommodation",
            "label": "Accommodation",
            "value": accommodation_type,
            "confirmed": bool(accommodation_type),
        },
        {
            "key": "constraints",
            "label": "Constraints",
            "value": ", ".join(constraints) if constraints else None,
            "confirmed": bool(constraints),
        },
    ]


def subagent_result_text(output: dict) -> str | None:
    """Latest text from a subagent node update.

    Result keys are irregular (weather_results, activity_results,
    rental_car_results, ...), so scan for the `*_results` suffix instead
    of hardcoding them. Also tolerates Anthropic-style content blocks.

    Args:
        output: raw node update dict from a subagent node.

    Returns:
        The latest result text (truncated past the char cap), or None
        when the update carries no usable text.
    """
    for key, value in output.items():
        if key.endswith("_results") and isinstance(value, list) and value:
            last = value[-1]
            if isinstance(last, list):
                last = "\n".join(
                    b.get("text", "") for b in last
                    if isinstance(b, dict) and b.get("type") == "text"
                )
            if isinstance(last, str) and last.strip():
                text = last.strip()
                if len(text) > AGENT_RESULT_MAX_CHARS:
                    return text[:AGENT_RESULT_MAX_CHARS] + "\n\n…(truncated)"
                return text
    return None


def conv_to_dict(conv) -> dict:
    """Conversation row -> sidebar list payload.

    Args:
        conv: a `Conversation` ORM row.

    Returns:
        The conversation as a frontend-ready dict (naive datetimes are
        assumed UTC).
    """
    updated = conv.updated_at
    if updated is not None and updated.tzinfo is None:
        updated = updated.replace(tzinfo=timezone.utc)
    return {
        "id": conv.id,
        "title": conv.title,
        "updatedAt": updated.isoformat() if updated else None,
        "messageIds": [],
    }


def stored_to_chat(msg) -> dict:
    """Persisted message row -> chat message payload (for rehydrate).

    Re-attaches the persisted side-channel payloads (destinations,
    subagent results, stats) so a reload restores the full bubbles.

    Args:
        msg: a `Message` ORM row.

    Returns:
        The message as a frontend-ready chat dict.
    """
    created = msg.created_at
    if created is not None and created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    out = {
        "id": f"srv-{msg.id}",
        "role": msg.role,
        "kind": msg.kind or "text",
        "text": msg.text or "",
        "createdAt": created.isoformat() if created else None,
    }
    if isinstance(msg.payload, dict) and "destinations" in msg.payload:
        out["destinations"] = msg.payload["destinations"]
    if isinstance(msg.payload, dict) and msg.payload.get("subagentResults"):
        out["subagentResults"] = [
            {"id": r.get("id", ""), "label": "", "text": r.get("text", "")}
            for r in msg.payload["subagentResults"]
            if isinstance(r, dict)
        ]
    if isinstance(msg.payload, dict) and isinstance(msg.payload.get("stats"), dict):
        out["stats"] = msg.payload["stats"]
    return out


def saved_plan_to_dict(row) -> dict:
    """SavedPlan row -> plans-library card payload.

    Args:
        row: a `SavedPlan` ORM row.

    Returns:
        The saved plan as a frontend-ready dict, with the destination and
        dates requirement values promoted to card subtitle fields.
    """
    created = row.created_at
    if created is not None and created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    payload = dict(row.plan or {})
    return {
        "id": str(row.id),
        "title": row.title,
        "description": row.description or "",
        "conversationId": row.conversation_id,
        "requirements": row.requirements or [],
        "plan": payload.get("plan") or [],
        "total": payload.get("total", 0),
        "currency": payload.get("currency"),
        "budget": payload.get("budget"),
        "overBudget": bool(payload.get("overBudget", False)),
        "createdAt": created.isoformat() if created else None,
        # Card subtitles prefer saved requirements; empty fallback keeps `next()` from raising.
        "destination": next(
            (r.get("value") for r in (row.requirements or []) if isinstance(r, dict) and r.get("key") == "destination" and r.get("value")),
            "",
        ),
        "dates": next(
            (r.get("value") for r in (row.requirements or []) if isinstance(r, dict) and r.get("key") == "dates" and r.get("value")),
            "",
        ),
    }
