"""Independently compare native JSON tokens and SQL identity controls with public facts."""

from pathlib import Path
from decimal import Decimal
from fractions import Fraction
from datetime import datetime, timezone
from dateutil.parser import isoparse
import argparse, csv, hashlib, json, re, sqlite3

ROOT = Path(__file__).resolve().parents[1]


def run(native):
    conditions = 0

    def require(ok, label):
        nonlocal conditions
        assert ok, label
        conditions += 1

    manifest = json.loads((ROOT / "data/capture_manifest.json").read_bytes())
    require(manifest["status"] == "PASS_CAPTURE_CONTROLS", "capture control gate")
    db = sqlite3.connect(":memory:")
    db.execute("CREATE TABLE native_keys(case_id TEXT, transaction_key TEXT)")
    raw_by_case = {}
    for item in manifest["requests"]:
        raw = (native / item["file"]).read_bytes()
        require(item["status"] == 200, "native status")
        require(len(raw) == item["bytes"], "native bytes")
        require(hashlib.sha256(raw).hexdigest() == item["sha256"], "native SHA256")
        if item["file"].endswith("-transactions.json"):
            data = json.loads(
                raw, parse_int=Decimal, parse_float=Decimal, parse_constant=Decimal
            )
            case = item["file"].split("-", 1)[0]
            raw_by_case[case] = data["results"]
            require(
                data["page_metadata"]["hasNext"] is False,
                "complete bounded source page",
            )
            db.executemany(
                "INSERT INTO native_keys VALUES (?,?)",
                [
                    (
                        case,
                        (
                            r.get("id")
                            if isinstance(r.get("id"), str) and r.get("id")
                            else None
                        ),
                    )
                    for r in data["results"]
                ],
            )
    grouped = {
        (case, key): count
        for case, key, count in db.execute(
            "SELECT case_id,transaction_key,COUNT(*) FROM native_keys GROUP BY case_id,transaction_key"
        )
    }
    with (ROOT / "data/transactions.csv").open(encoding="utf-8", newline="") as f:
        projected = list(csv.DictReader(f))
    expected_count = sum(len(rows) for rows in raw_by_case.values())
    require(len(projected) == expected_count, "all native records projected")
    require(
        len({(r["case"], r["source_row"]) for r in projected}) == expected_count,
        "one projection per native row",
    )
    cases = json.loads((ROOT / "data/cases.json").read_bytes())
    require(len(cases) == 20 == len(raw_by_case), "fixed 20 cases")
    first = json.loads((native / "awards-first.json").read_bytes())["results"]
    final = json.loads((native / "awards-final.json").read_bytes())["results"]
    fields = json.loads((ROOT / "data/source_contract.json").read_bytes())[
        "search_request"
    ]["fields"]
    require(
        [{k: r[k] for k in fields} for r in first]
        == [{k: r[k] for k in fields} for r in final],
        "two actual current search observations",
    )
    for index, case in enumerate(cases):
        source = first[index]
        require(case["case"] == f"C{index+1:02d}", "fixed source-page case order")
        for public, field in [
            ("generated_award_id", "generated_internal_id"),
            ("award_id", "Award ID"),
            ("base_date", "Base Obligation Date"),
            ("contract_type", "Contract Award Type"),
        ]:
            require(case[public] == source[field], ("native case field", public))
        origin = datetime.strptime(case["base_date"], "%Y-%m-%d").date()
        require(origin.year == 2024, "source base year")
        require(
            (datetime.now(timezone.utc).date() - origin).days >= 365,
            "full asserted calendar follow-up elapsed",
        )
        require(
            source["Awarding Agency"]
            == "National Aeronautics and Space Administration",
            "fixed source agency",
        )
        before = json.loads(
            (native / (case["case"] + "-count-before.json")).read_bytes()
        )["transactions"]
        after = json.loads(
            (native / (case["case"] + "-count-after.json")).read_bytes()
        )["transactions"]
        require(
            before
            == after
            == len(raw_by_case[case["case"]])
            == case["captured_records"],
            "native count agreement",
        )
    for row in projected:
        source = raw_by_case[row["case"]][int(row["source_row"]) - 1]
        key = source.get("id")
        key = key if isinstance(key, str) and key else None
        state = (
            "MISSING"
            if key is None
            else "SINGLETON" if grouped[(row["case"], key)] == 1 else "DUPLICATE"
        )
        require(
            row["transaction_id"] == (key or ""), "native government transaction key"
        )
        require(row["identity_state"] == state, "independent SQL key multiplicity")
        action = source.get("action_date")
        require(
            row["action_date"] == (action if isinstance(action, str) else ""),
            "native source calendar token",
        )
        try:
            valid = (
                isinstance(action, str)
                and bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}", action))
                and isoparse(action).strftime("%Y-%m-%d") == action
            )
        except (ValueError, TypeError):
            valid = False
        require(
            row["date_state"] == ("VALID" if valid else "INVALID_OR_MISSING"),
            "independent source date validation",
        )
        require(
            row["type_code"] == source.get("type", "")
            and row["type_code"] in ["A", "B", "C", "D"],
            "native contract type",
        )
        modification = source.get("modification_number")
        require(
            modification is None or isinstance(modification, str),
            "source modification scalar definition",
        )
        require(
            row["modification_token"] == (modification or ""),
            "unaltered source modification label",
        )
        value = source.get("federal_action_obligation")
        numeric = type(value) is Decimal
        state = (
            "MISSING"
            if value is None
            else (
                "NONNUMERIC"
                if not numeric
                else "FINITE" if value.is_finite() else "NONFINITE"
            )
        )
        require(row["money_state"] == state, "native amount kind")
        if state == "FINITE":
            require(
                Fraction(row["money_token"]) == Fraction(value),
                "exact native numeric value",
            )
        else:
            require(row["money_token"] == "", "unknown amount not zero")
    paths = [
        "data/cases.json",
        "data/transactions.csv",
        "data/capture_manifest.json",
        "data/source_contract.json",
    ]
    receipt = dict(
        status="PASS",
        finite_conditions=conditions,
        cases=len(cases),
        native_records=expected_count,
        hashes={
            name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
            for name in paths
        },
        methods="Separate native JSON Decimal parser, SQLite key multiplicity, datetime/dateutil calendar validation and exact Fraction values; no production projection import.",
        scope="Captured native records and specific current consistency controls only; not original-vintage completeness, actual legal modifications or staff effort.",
    )
    (ROOT / "data/native_verification.json").write_bytes(
        (json.dumps(receipt, indent=2) + "\n").encode()
    )
    print(json.dumps(receipt))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", type=Path, required=True)
    run(parser.parse_args().source_dir)
