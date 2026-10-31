"""Exact current-record accounting; counts are source actions, not staff effort."""

from collections import Counter
from datetime import date
from decimal import Decimal, localcontext
from fractions import Fraction


def calendar(value):
    if not isinstance(value, str):
        return None
    try:
        parsed = date.fromisoformat(value)
        return parsed if parsed.isoformat() == value else None
    except ValueError:
        return None


def amount(row):
    if row.get("money_state") != "FINITE":
        return None
    try:
        value = Decimal(row["money_token"])
        return value if value.is_finite() else None
    except (ValueError, TypeError, ArithmeticError, KeyError):
        return None


def account(case, rows, horizon=365):
    assert type(horizon) is int and horizon > 0
    origin = calendar(case["base_date"])
    assert origin is not None
    keys = Counter(
        r.get("transaction_id")
        for r in rows
        if isinstance(r.get("transaction_id"), str) and r.get("transaction_id")
    )
    classified = []
    window = []
    for row in rows:
        key = row.get("transaction_id")
        action = calendar(row.get("action_date"))
        delta = (action - origin).days if action else None
        if not isinstance(key, str) or not key:
            scope = "MISSING_KEY"
        elif keys[key] != 1:
            scope = "DUPLICATE_KEY"
        elif delta is None:
            scope = "UNKNOWN_DATE"
        elif delta < 0:
            scope = "BEFORE_ORIGIN"
        elif delta >= horizon:
            scope = "AT_OR_AFTER_HORIZON"
        else:
            scope = "IN_WINDOW"
            window.append(row)
        classified.append(
            dict(
                case=case["case"],
                source_row=row["source_row"],
                transaction_id=key or "",
                delta_days="" if delta is None else delta,
                scope=scope,
                money_state=row.get("money_state", "MISSING"),
                money_token=row.get("money_token", ""),
            )
        )
    counts = Counter(r["scope"] for r in classified)
    values = [amount(row) for row in window]
    known = [v for v in values if v is not None]
    complete = (
        bool(window)
        and len(known) == len(window)
        and not any(counts[k] for k in ["MISSING_KEY", "DUPLICATE_KEY", "UNKNOWN_DATE"])
    )
    with localcontext() as context:
        # Cover the complete decimal exponent span and the possible carry digits.
        context.prec = max(
            80,
            max((v.adjusted() for v in known), default=0)
            - min((v.as_tuple().exponent for v in known), default=0)
            + len(str(len(known)))
            + 4,
        )
        positive = sum((v for v in known if v > 0), Decimal(0))
        negative = sum((v for v in known if v < 0), Decimal(0))
        net = positive + negative
        gross = positive - negative
    offset = (
        (Fraction(gross) - abs(Fraction(net))) / Fraction(gross)
        if complete and gross > 0
        else None
    )
    dates = Counter(r["action_date"] for r in window)
    modification_tokens = [
        r["modification_token"] for r in window if r["modification_token"]
    ]
    summary = dict(
        case=case["case"],
        base_date=case["base_date"],
        all_source_records=len(rows),
        missing_key_records=counts["MISSING_KEY"],
        duplicate_key_records=counts["DUPLICATE_KEY"],
        unknown_date_records=counts["UNKNOWN_DATE"],
        before_origin_records=counts["BEFORE_ORIGIN"],
        at_or_after_horizon_records=counts["AT_OR_AFTER_HORIZON"],
        window_actions=len(window),
        finite_money_actions=len(known),
        unknown_money_actions=len(window) - len(known),
        positive_actions=sum(v > 0 for v in known),
        negative_actions=sum(v < 0 for v in known),
        zero_actions=sum(v == 0 for v in known),
        origin_day_actions=dates.get(case["base_date"], 0),
        shared_calendar_day_actions=sum(n for n in dates.values() if n > 1),
        distinct_modification_tokens=len(set(modification_tokens)),
        missing_modification_tokens=len(window) - len(modification_tokens),
        money_complete=complete,
        positive_usd=format(positive, "f") if complete else "",
        negative_signed_usd=format(negative, "f") if complete else "",
        net_usd=format(net, "f") if complete else "",
        gross_absolute_usd=format(gross, "f") if complete else "",
        net_offset_fraction=str(offset) if offset is not None else "",
    )
    return summary, classified


def rank_queues(accounts, capacity=5):
    assert type(capacity) is int and capacity > 0
    joint = [r for r in accounts if r["money_complete"]]
    counts = sorted(joint, key=lambda r: (-r["window_actions"], r["case"]))
    dollars = sorted(joint, key=lambda r: (-Fraction(r["net_usd"]), r["case"]))
    k = min(capacity, len(joint))
    left = [r["case"] for r in counts[:k]]
    right = [r["case"] for r in dollars[:k]]
    a, b = set(left), set(right)
    union = a | b
    comparison = dict(
        review_capacity=capacity,
        joint_eligible_cases=len(joint),
        selected_per_queue=k,
        action_count_queue=left,
        net_obligation_queue=right,
        overlap_count=len(a & b),
        union_count=len(union),
        jaccard_fraction=str(Fraction(len(a & b), len(union))) if union else "",
        scope="Fixed illustrative capacity; current source-record actions, not validated staffing effort or vendor quality.",
    )
    ranks = []
    for row in accounts:
        case = row["case"]
        ranks.append(
            dict(
                case=case,
                joint_eligible=row["money_complete"],
                action_count_rank=next(
                    (i + 1 for i, r in enumerate(counts) if r["case"] == case), ""
                ),
                net_obligation_rank=next(
                    (i + 1 for i, r in enumerate(dollars) if r["case"] == case), ""
                ),
                in_action_count_queue=case in a,
                in_net_obligation_queue=case in b,
            )
        )
    return comparison, ranks
