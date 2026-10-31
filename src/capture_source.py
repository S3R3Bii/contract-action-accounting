"""Capture one fixed current award page and complete bounded transaction histories."""

from pathlib import Path
from datetime import date, datetime, timezone
from urllib.parse import quote
import argparse, hashlib, json, subprocess
import requests

ROOT = Path(__file__).resolve().parents[1]


def run(out):
    contract = json.loads((ROOT / "data/source_contract.json").read_bytes())
    out = out.resolve()
    assert not out.exists()
    out.mkdir(parents=True)
    requests_log = []
    cases = []

    def save(name, method, url, body=None):
        started = datetime.now(timezone.utc).isoformat()
        response = requests.request(method, url, json=body, timeout=45)
        raw = response.content
        (out / name).write_bytes(raw)
        item = dict(
            file=name,
            method=method,
            url=url,
            request=body,
            started_utc=started,
            captured_utc=datetime.now(timezone.utc).isoformat(),
            status=response.status_code,
            bytes=len(raw),
            sha256=hashlib.sha256(raw).hexdigest(),
        )
        requests_log.append(item)
        (out / "capture_manifest.json").write_bytes(
            (
                json.dumps(
                    dict(
                        requests=requests_log, cases=cases, status="CAPTURE_IN_PROGRESS"
                    ),
                    indent=2,
                )
                + "\n"
            ).encode()
        )
        response.raise_for_status()
        return json.loads(raw)

    first = save(
        "awards-first.json",
        "POST",
        contract["search_endpoint"],
        contract["search_request"],
    )
    rows = first["results"]
    assert len(rows) == 20, "fixed first-page count"
    keys = [r["generated_internal_id"] for r in rows]
    assert len(set(keys)) == len(keys) and all(
        isinstance(k, str) and k.startswith("CONT_AWD_") for k in keys
    )
    assert [r["Award ID"] for r in rows] == sorted(
        r["Award ID"] for r in rows
    ), "source Award ID order"
    for i, row in enumerate(rows, 1):
        base = date.fromisoformat(row["Base Obligation Date"][:10])
        assert (
            base.year == 2024 and (datetime.now(timezone.utc).date() - base).days >= 365
        )
        assert row["Awarding Agency"] == "National Aeronautics and Space Administration"
        assert (
            isinstance(row["Awarding Agency Code"], str) and row["Awarding Agency Code"]
        ), "source agency code retained without cross-system conversion"
        assert (
            isinstance(row["Contract Award Type"], str) and row["Contract Award Type"]
        ), "procurement source type label retained"
        case = f"C{i:02d}"
        key = row["generated_internal_id"]
        url = contract["count_endpoint"].format(award_id=quote(key, safe=""))
        before = save(case + "-count-before.json", "GET", url)
        count = before["transactions"]
        assert type(count) is int and 0 < count <= contract["fixed_history_limit"]
        body = dict(
            award_id=key,
            page=1,
            sort="action_date",
            order="asc",
            limit=contract["fixed_history_limit"],
        )
        history = save(
            case + "-transactions.json", "POST", contract["transactions_endpoint"], body
        )
        after = save(case + "-count-after.json", "GET", url)
        observed = history["results"]
        assert (
            len(observed) == count == after["transactions"]
        ), "current count consistency"
        assert (
            history["page_metadata"]["hasNext"] is False
        ), "partial history not accepted"
        ids = [r["id"] for r in observed]
        assert len(set(ids)) == len(ids) and all(
            isinstance(k, str) and k for k in ids
        ), "transaction key consistency"
        assert all(
            r["type"] in ["A", "B", "C", "D"] for r in observed
        ), "contract history only"
        cases.append(
            dict(
                case=case,
                generated_award_id=key,
                award_id=row["Award ID"],
                base_date=base.isoformat(),
                contract_type=row["Contract Award Type"],
                captured_records=count,
                before_count=before["transactions"],
                after_count=after["transactions"],
            )
        )
        print(json.dumps(dict(case=case, captured_records=count)))
    final = save(
        "awards-final.json",
        "POST",
        contract["search_endpoint"],
        contract["search_request"],
    )
    fields = contract["search_request"]["fields"]
    assert [{k: r[k] for k in fields} for r in first["results"]] == [
        {k: r[k] for k in fields} for r in final["results"]
    ], "selected current source assertions changed"
    manifest = dict(
        status="PASS_CAPTURE_CONTROLS",
        requests=requests_log,
        cases=cases,
        protocol_commit=subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        qualification="Two agreeing search observations and per-case counts detect specific changes; not atomicity, historical completeness or original delivery proof.",
    )
    (out / "capture_manifest.json").write_bytes(
        (json.dumps(manifest, indent=2) + "\n").encode()
    )
    (ROOT / "data/capture_manifest.json").write_bytes(
        (json.dumps(manifest, indent=2) + "\n").encode()
    )
    print(
        "CAPTURE_CONTROLS_PASS",
        len(cases),
        sum(c["captured_records"] for c in cases),
        len(requests_log),
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    run(parser.parse_args().out)
