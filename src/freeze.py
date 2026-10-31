"""Record actual source and method dependencies before comparison execution."""

from pathlib import Path
import argparse, hashlib, json, subprocess

ROOT = Path(__file__).resolve().parents[1]


def main(create):
    path = ROOT / "PLAN_FREEZE.json"
    if create:
        assert not path.exists()
        names = [
            str(p.relative_to(ROOT)).replace("\\", "/")
            for folder in ["data", "src", "tests"]
            for p in (ROOT / folder).glob("*")
            if p.is_file() and p.suffix in [".py", ".json", ".csv"]
        ]
        names += [
            "PROTOCOL.md",
            "DATA_RIGHTS.md",
            "SOURCE_HISTORY.md",
            "requirements.txt",
            "requirements-source.txt",
        ]
        manifest = dict(
            source_checkpoint=subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
            ).strip(),
            hashes={
                n: hashlib.sha256((ROOT / n).read_bytes()).hexdigest()
                for n in sorted(names)
            },
            qualification="Actual source/method dependency hashes fixed before accounting/ranking comparisons. Current source values were visible during capture and reconciliation; not blinded.",
        )
        path.write_bytes((json.dumps(manifest, indent=2) + "\n").encode())
    value = json.loads(path.read_bytes())
    for name, sha in value["hashes"].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == sha, (
            "frozen dependency changed",
            name,
        )
    print(
        json.dumps(
            dict(
                status="PASS",
                dependencies=len(value["hashes"]),
                freeze_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                source_checkpoint=value["source_checkpoint"],
            )
        )
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--create", action="store_true")
    main(p.parse_args().create)
