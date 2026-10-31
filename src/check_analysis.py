"""Reconstruct every account/probe/queue from source rows with SQL and exact rationals."""

from pathlib import Path
from datetime import datetime
from fractions import Fraction
from collections import Counter
from dateutil.parser import isoparse
import csv, json, sqlite3

ROOT = Path(__file__).resolve().parents[1]


def read_csv(name):
    with (ROOT / name).open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def main():
    n = 0

    def require(ok, label):
        nonlocal n
        assert ok, label
        n += 1

    cases = json.loads((ROOT / "data/cases.json").read_bytes())
    source = read_csv("data/transactions.csv")
    db = sqlite3.connect(":memory:")
    db.execute(
        "CREATE TABLE r(case_id TEXT, source_row INTEGER, tx TEXT, action_date TEXT, day INTEGER, token TEXT, amount TEXT, money_kind TEXT)"
    )
    for row in source:
        origin = next(c["base_date"] for c in cases if c["case"] == row["case"])
        if row["date_state"] == "VALID":
            parsed = isoparse(row["action_date"])
            delta = (parsed - isoparse(origin)).days
            sql_day = db.execute(
                "SELECT CAST(julianday(?) - julianday(?) AS INTEGER)",
                (row["action_date"], origin),
            ).fetchone()[0]
            require(delta == sql_day, "independent SQL/calendar day agreement")
        else:
            delta = None
        db.execute(
            "INSERT INTO r VALUES (?,?,?,?,?,?,?,?)",
            (
                row["case"],
                int(row["source_row"]),
                row["transaction_id"],
                row["action_date"],
                delta,
                row["modification_token"],
                row["money_token"],
                row["money_state"],
            ),
        )
    actual = {r["case"]: r for r in read_csv("results/case_accounts.csv")}
    require(set(actual) == {r["case"] for r in cases}, "complete cases")
    expected = {}
    classifications = {
        (r["case"], int(r["source_row"])): r
        for r in read_csv("results/row_classification.csv")
    }
    require(len(classifications) == len(source), "complete row classifications")
    probes = {
        (r["case"], int(r["horizon_days"])): int(r["window_actions"])
        for r in read_csv("results/cumulative_probes.csv")
    }
    require(len(probes) == len(cases) * 3, "all fixed probes")
    for case in cases:
        key = case["case"]
        row = actual[key]
        records = db.execute(
            "SELECT source_row,tx,action_date,day,token,amount,money_kind FROM r WHERE case_id=? ORDER BY source_row",
            (key,),
        ).fetchall()
        multiplicities = dict(
            db.execute("SELECT tx,COUNT(*) FROM r WHERE case_id=? GROUP BY tx", (key,))
        )
        states = Counter()
        window = []
        for index, tx, day_token, delta, token, value, kind in records:
            status = (
                "MISSING_KEY"
                if not tx
                else (
                    "DUPLICATE_KEY"
                    if multiplicities[tx] > 1
                    else (
                        "UNKNOWN_DATE"
                        if delta is None
                        else (
                            "BEFORE_ORIGIN"
                            if delta < 0
                            else "AT_OR_AFTER_HORIZON" if delta >= 365 else "IN_WINDOW"
                        )
                    )
                )
            )
            states[status] += 1
            if status == "IN_WINDOW":
                window.append((day_token, delta, token, value, kind))
            result = classifications[(key, index)]
            for name, value_expected in [
                ("transaction_id", tx),
                ("delta_days", "" if delta is None else str(delta)),
                ("scope", status),
                ("money_state", kind),
                ("money_token", value),
            ]:
                require(
                    result[name] == value_expected,
                    ("complete source-row classification", key, index, name),
                )
        known = [Fraction(r[3]) for r in window if r[4] == "FINITE"]
        complete = (
            bool(window)
            and len(known) == len(window)
            and not sum(
                states[x] for x in ["MISSING_KEY", "DUPLICATE_KEY", "UNKNOWN_DATE"]
            )
        )
        pos = sum((v for v in known if v > 0), Fraction())
        neg = sum((v for v in known if v < 0), Fraction())
        net = pos + neg
        gross = pos - neg
        dates = Counter(r[0] for r in window)
        tokens = [r[2] for r in window if r[2]]
        controls = dict(
            all_source_records=len(records),
            missing_key_records=states["MISSING_KEY"],
            duplicate_key_records=states["DUPLICATE_KEY"],
            unknown_date_records=states["UNKNOWN_DATE"],
            before_origin_records=states["BEFORE_ORIGIN"],
            at_or_after_horizon_records=states["AT_OR_AFTER_HORIZON"],
            window_actions=len(window),
            finite_money_actions=len(known),
            unknown_money_actions=len(window) - len(known),
            positive_actions=sum(v > 0 for v in known),
            negative_actions=sum(v < 0 for v in known),
            zero_actions=sum(v == 0 for v in known),
            origin_day_actions=dates.get(case["base_date"], 0),
            shared_calendar_day_actions=sum(v for v in dates.values() if v > 1),
            distinct_modification_tokens=len(set(tokens)),
            missing_modification_tokens=len(window) - len(tokens),
        )
        require(row["base_date"] == case["base_date"], "source base date retained")
        for name, value in controls.items():
            require(
                int(row[name]) == value, ("independent complete case count", key, name)
            )
        require(
            row["money_complete"] == str(bool(complete)),
            "monetary and calendar completeness",
        )
        for name, value in [
            ("positive_usd", pos),
            ("negative_signed_usd", neg),
            ("net_usd", net),
            ("gross_absolute_usd", gross),
        ]:
            require(
                Fraction(row[name]) == value if complete else row[name] == "",
                ("exact rational financial total", key, name),
            )
        offset = (gross - abs(net)) / gross if complete and gross > 0 else None
        require(
            (
                row["net_offset_fraction"] == str(offset)
                if offset is not None
                else row["net_offset_fraction"] == ""
            ),
            "net offset exact fraction or unavailable",
        )
        require(sum(states.values()) == len(records), "complete source partition")
        for horizon in [30, 90, 365]:
            count = db.execute(
                "SELECT COUNT(*) FROM r WHERE case_id=? AND day>=0 AND day<? AND tx!='' AND tx IN (SELECT tx FROM r WHERE case_id=? GROUP BY tx HAVING COUNT(*)=1)",
                (key, horizon, key),
            ).fetchone()[0]
            require(
                probes[(key, horizon)] == count,
                "complete independent SQL horizon probe",
            )
        expected[key] = dict(
            actions=len(window), complete=bool(complete), net=net, counts=controls
        )
    joint = [k for k, v in expected.items() if v["complete"]]
    by_count = sorted(joint, key=lambda k: (-expected[k]["actions"], k))
    by_money = sorted(joint, key=lambda k: (-expected[k]["net"], k))
    k = min(5, len(joint))
    left = by_count[:k]
    right = by_money[:k]
    a = set(left)
    b = set(right)
    summary = json.loads((ROOT / "results/summary.json").read_bytes())
    queues = summary["queues"]
    for name, value in dict(
        review_capacity=5,
        joint_eligible_cases=len(joint),
        selected_per_queue=k,
        action_count_queue=left,
        net_obligation_queue=right,
        overlap_count=len(a & b),
        union_count=len(a | b),
        jaccard_fraction=str(Fraction(len(a & b), len(a | b))) if a | b else "",
    ).items():
        require(queues[name] == value, ("complete queue comparison", name))
    ranks = read_csv("results/queue_ranks.csv")
    require(len(ranks) == 20, "all case ranks")
    for row in ranks:
        key = row["case"]
        require(row["joint_eligible"] == str(key in joint), "joint rank eligibility")
        require(
            (
                row["action_count_rank"] == str(by_count.index(key) + 1)
                if key in joint
                else row["action_count_rank"] == ""
            ),
            "complete action rank",
        )
        require(
            (
                row["net_obligation_rank"] == str(by_money.index(key) + 1)
                if key in joint
                else row["net_obligation_rank"] == ""
            ),
            "complete dollar rank",
        )
        require(
            row["in_action_count_queue"] == str(key in a)
            and row["in_net_obligation_queue"] == str(key in b),
            "complete membership",
        )
    headlines = dict(
        cases=20,
        native_records=len(source),
        window_actions=sum(v["actions"] for v in expected.values()),
        zero_amount_actions=sum(v["counts"]["zero_actions"] for v in expected.values()),
        negative_amount_actions=sum(
            v["counts"]["negative_actions"] for v in expected.values()
        ),
        unknown_amount_actions=sum(
            v["counts"]["unknown_money_actions"] for v in expected.values()
        ),
        financially_complete_cases=len(joint),
    )
    for name, value in headlines.items():
        require(summary[name] == value, ("headline from complete source cases", name))
    require(
        summary["original_preaward_classifier"] == "UNEXECUTED"
        and summary["historical_publication_evidence"] == "UNESTABLISHED",
        "original hold retained",
    )
    exercises = json.loads((ROOT / "results/exercise.json").read_bytes())
    inputs = json.loads((ROOT / "data/exercise_inputs.json").read_bytes())
    require(len(exercises) == len(inputs) == 7, "complete authored requests")
    for i, (request, result) in enumerate(zip(inputs, exercises)):
        require(request == result["request"], "actual complete request")
        answer = result["result"]
        key = request["case"]
        accepted = request["measure"] == "CURRENT_ACTION_ACCOUNT" or (
            request["measure"] == "CURRENT_OBLIGATION_ACCOUNT"
            and expected[key]["complete"]
        )
        require(answer["accepted"] == accepted, "independent source eligibility")
        if accepted:
            target = (
                expected[key]["actions"]
                if request["measure"] == "CURRENT_ACTION_ACCOUNT"
                else expected[key]["net"]
            )
            require(
                Fraction(answer["value"]) == target,
                "actual source-backed exercise value",
            )
            require(
                answer["historical_publication_known"] is False,
                "exercise qualification",
            )
        else:
            require(
                answer["reason"]
                == (
                    "INCOMPLETE_MONEY_OR_WINDOW"
                    if request["measure"] == "CURRENT_OBLIGATION_ACCOUNT"
                    else "UNSUPPORTED_CONVERSION"
                ),
                "unsupported or incomplete request rejected",
            )
    receipt = dict(
        status="PASS",
        finite_conditions=n,
        cases=20,
        source_rows=len(source),
        probes=len(probes),
        examples=len(exercises),
        methods="Independent dateutil plus SQLite day/identity/count controls and exact Fraction accounting/ranking; no production aggregation or exercise import.",
        scope="Every current saved case, source-row classification, probe, queue rank and authored request; not universal correctness or verified staffing effort.",
    )
    (ROOT / "results/independent_check.json").write_bytes(
        (json.dumps(receipt, indent=2) + "\n").encode()
    )
    print(json.dumps(receipt))


if __name__ == "__main__":
    main()
