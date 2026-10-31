"""Reproduce frozen saved-data accounting and exact outputs in a new directory."""

from pathlib import Path
import argparse, hashlib, json, subprocess, sys

ROOT = Path(__file__).resolve().parents[1]


def run(out, analysis_only):
    assert (
        not out.exists() and out.resolve() != (ROOT / "results").resolve()
    ), "use a new separate directory"

    def call(name, *args):
        subprocess.run(
            [sys.executable, str(ROOT / "src" / name), *map(str, args)],
            cwd=ROOT,
            check=True,
        )

    call("freeze.py")
    call("check_source.py")
    before = {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in (ROOT / "data").iterdir()
        if p.is_file()
    }
    call("analyze.py", "--out", out)
    call("exercise.py", "--out", out)
    names = [
        "case_accounts.csv",
        "row_classification.csv",
        "cumulative_probes.csv",
        "queue_ranks.csv",
        "summary.json",
        "exercise.json",
    ]
    for name in names:
        assert (out / name).read_bytes() == (ROOT / "results" / name).read_bytes(), name
    call("check_analysis.py")
    subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
        cwd=ROOT,
        check=True,
    )
    if not analysis_only:
        call("check_figures.py")
        call("check_paper.py")
    after = {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in (ROOT / "data").iterdir()
        if p.is_file()
    }
    assert before == after
    receipt = dict(
        status="PASS",
        python=sys.version.split()[0],
        reproduced_files=names,
        unchanged_source_files=len(before),
        native_redownload=False,
        scope="Frozen minimal current source replay, not independent reacquisition or original-vintage evidence.",
    )
    (out / "REPLAY_RECEIPT.json").write_bytes(
        (json.dumps(receipt, indent=2) + "\n").encode()
    )
    print("PASS_SAVED_DATA_REPLAY", sys.version.split()[0], len(names), len(before))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--analysis-only", action="store_true")
    a = p.parse_args()
    run(a.out, a.analysis_only)
