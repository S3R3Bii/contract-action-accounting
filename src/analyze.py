"""Run the frozen complete current-account comparison."""

from pathlib import Path
from collections import defaultdict
import argparse, csv, json
from accounting import account, rank_queues

ROOT = Path(__file__).resolve().parents[1]


def run(out):
    out.mkdir(parents=True, exist_ok=True)
    cases = json.loads((ROOT / "data/cases.json").read_bytes())
    by_case = defaultdict(list)
    with (ROOT / "data/transactions.csv").open(encoding="utf-8", newline="") as stream:
        for row in csv.DictReader(stream):
            by_case[row["case"]].append(row)
    accounts = []
    classifications = []
    probes = []
    for case in cases:
        summary, classified = account(case, by_case[case["case"]])
        accounts.append(summary)
        classifications += classified
        for horizon in [30, 90, 365]:
            result, _ = account(case, by_case[case["case"]], horizon)
            probes.append(
                dict(
                    case=case["case"],
                    horizon_days=horizon,
                    window_actions=result["window_actions"],
                )
            )
    queues, ranks = rank_queues(accounts)
    for name, rows in [
        ("case_accounts.csv", accounts),
        ("row_classification.csv", classifications),
        ("cumulative_probes.csv", probes),
        ("queue_ranks.csv", ranks),
    ]:
        with (out / name).open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
    summary = dict(
        cases=len(cases),
        native_records=sum(r["all_source_records"] for r in accounts),
        window_actions=sum(r["window_actions"] for r in accounts),
        zero_amount_actions=sum(r["zero_actions"] for r in accounts),
        negative_amount_actions=sum(r["negative_actions"] for r in accounts),
        unknown_amount_actions=sum(r["unknown_money_actions"] for r in accounts),
        financially_complete_cases=sum(r["money_complete"] for r in accounts),
        queues=queues,
        interpretation="One current source view of fixed historical action windows; financial/action measures are not historical availability, legal modification counts, staff hours, paid cash, contract quality or vendor risk.",
        original_preaward_classifier="UNEXECUTED",
        historical_publication_evidence="UNESTABLISHED",
    )
    (out / "summary.json").write_bytes((json.dumps(summary, indent=2) + "\n").encode())
    print(json.dumps(summary))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--out", type=Path, default=ROOT / "results")
    run(p.parse_args().out)
