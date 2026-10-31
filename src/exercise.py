"""Expose actual case accounts while rejecting unsupported measurement conversions."""

from pathlib import Path
import argparse, csv, json

ROOT = Path(__file__).resolve().parents[1]
SUPPORTED = {"CURRENT_ACTION_ACCOUNT", "CURRENT_OBLIGATION_ACCOUNT"}


def interpret(request, accounts):
    if not isinstance(request, dict):
        return dict(accepted=False, reason="INVALID_REQUEST")
    case = request.get("case")
    matches = [r for r in accounts if r["case"] == case]
    if len(matches) != 1:
        return dict(accepted=False, reason="CASE_NOT_ESTABLISHED")
    kind = request.get("measure")
    if kind not in SUPPORTED:
        return dict(
            accepted=False,
            reason="UNSUPPORTED_CONVERSION",
            detail="Current counts and obligation fields do not establish publication timing, staff hours, vendor quality or future modifications.",
        )
    row = matches[0]
    if kind == "CURRENT_OBLIGATION_ACCOUNT" and row["money_complete"] != "True":
        return dict(accepted=False, reason="INCOMPLETE_MONEY_OR_WINDOW")
    if kind == "CURRENT_ACTION_ACCOUNT":
        return dict(
            accepted=True,
            case=case,
            measure=kind,
            value=row["window_actions"],
            unit="eligible current source transaction records in fixed 365-day calendar window",
            historical_publication_known=False,
        )
    return dict(
        accepted=True,
        case=case,
        measure=kind,
        value=row["net_usd"],
        unit="reported signed USD obligations in the current source view; not outlays",
        historical_publication_known=False,
    )


def run(out):
    with (out / "case_accounts.csv").open(encoding="utf-8", newline="") as f:
        accounts = list(csv.DictReader(f))
    inputs = json.loads((ROOT / "data/exercise_inputs.json").read_bytes())
    output = [dict(request=r, result=interpret(r, accounts)) for r in inputs]
    out.mkdir(parents=True, exist_ok=True)
    (out / "exercise.json").write_bytes((json.dumps(output, indent=2) + "\n").encode())
    print(
        json.dumps(
            dict(
                examples=len(output),
                accepted=sum(r["result"]["accepted"] for r in output),
            )
        )
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--out", type=Path, default=ROOT / "results")
    run(p.parse_args().out)
