"""Verify saved native-bound projections without redownloading mutable sources."""

from pathlib import Path
from datetime import datetime
from fractions import Fraction
from collections import Counter
import csv, hashlib, json, re

ROOT = Path(__file__).resolve().parents[1]


def main():
    n = 0

    def require(ok, label):
        nonlocal n
        assert ok, label
        n += 1

    native = json.loads((ROOT / "data/native_verification.json").read_bytes())
    require(
        native["status"] == "PASS" and native["finite_conditions"] == 1768,
        "native receipt",
    )
    for name, digest in native["hashes"].items():
        require(
            hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest,
            "native-bound source SHA256",
        )
    manifest = json.loads((ROOT / "data/capture_manifest.json").read_bytes())
    require(
        manifest["status"] == "PASS_CAPTURE_CONTROLS", "complete captured-history gate"
    )
    require(len(manifest["requests"]) == 62, "two search and 60 per-award responses")
    for item in manifest["requests"]:
        require(item["status"] == 200, "actual native HTTP status")
        require(
            bool(re.fullmatch("[0-9a-f]{64}", item["sha256"])),
            "actual native hash format",
        )
        require(
            item["url"].startswith("https://api.usaspending.gov/api/v2/"),
            "official endpoint",
        )
        require(
            datetime.fromisoformat(item["captured_utc"]).tzinfo is not None,
            "aware capture time",
        )
    cases = json.loads((ROOT / "data/cases.json").read_bytes())
    require(
        len(cases) == 20 and len({r["generated_award_id"] for r in cases}) == 20,
        "fixed unique cohort",
    )
    with (ROOT / "data/transactions.csv").open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    require(len(rows) == 153, "all captured source rows")
    require(
        len({(r["case"], r["source_row"]) for r in rows}) == len(rows),
        "unique source row mapping",
    )
    known = {r["case"]: r for r in cases}
    for case in cases:
        matches = [r for r in rows if r["case"] == case["case"]]
        require(len(matches) == case["captured_records"], "case count completeness")
        require(
            case["base_date"].startswith("2024-")
            and bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}", case["base_date"])),
            "source calendar origin",
        )
        require(
            {int(r["source_row"]) for r in matches} == set(range(1, len(matches) + 1)),
            "complete source row indices",
        )
    identities = Counter((r["case"], r["transaction_id"]) for r in rows)
    for row in rows:
        require(row["case"] in known, "known fixed case")
        require(
            row["identity_state"] == "SINGLETON"
            and bool(row["transaction_id"])
            and identities[(row["case"], row["transaction_id"])] == 1,
            "native singleton record identity",
        )
        require(row["type_code"] in ["A", "B", "C", "D"], "contract-only population")
        try:
            valid = (
                bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}", row["action_date"]))
                and datetime.strptime(row["action_date"], "%Y-%m-%d").strftime(
                    "%Y-%m-%d"
                )
                == row["action_date"]
            )
        except ValueError:
            valid = False
        require(
            row["date_state"] == ("VALID" if valid else "INVALID_OR_MISSING"),
            "source calendar eligibility",
        )
        if row["money_state"] == "FINITE":
            require(bool(row["money_token"]), "finite numeric token retained")
            Fraction(row["money_token"])
            n += 1
        else:
            require(
                row["money_token"] == ""
                and row["money_state"] in ["MISSING", "NONNUMERIC", "NONFINITE"],
                "unknown money retained",
            )
    print(
        json.dumps(
            dict(
                status="PASS",
                finite_conditions=n,
                cases=len(cases),
                source_rows=len(rows),
                scope="Exact native-bound saved projection, complete current row mapping and explicit field eligibility; not original-vintage or staff-task validation.",
            )
        )
    )


if __name__ == "__main__":
    main()
