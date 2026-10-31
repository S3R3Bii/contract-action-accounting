"""Independently verify used TeX bindings, all PDF table rows and publication scope."""

from pathlib import Path
from decimal import Decimal, localcontext
from fractions import Fraction
import csv, hashlib, json, re, unicodedata
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    if name.endswith(".csv"):
        with (ROOT / name).open(encoding="utf-8", newline="") as f:
            return list(csv.DictReader(f))
    return json.loads((ROOT / name).read_bytes())


def expected(binding):
    value = load(binding["file"])
    if binding["query"] is not None:
        matched = [
            r for r in value if all(r[k] == v for k, v in binding["query"].items())
        ]
        assert len(matched) == 1
        value = matched[0]
    if binding["operation"] == "sum":
        value = sum((Fraction(r[binding["field"]]) for r in value), Fraction())
    else:
        for key in binding["field"] or []:
            value = value[key]
        if binding["operation"] == "length":
            value = len(value)
    operation = binding["operation"]
    if operation == "money2":
        return format(Decimal(value), ",.2f")
    if operation == "commas":
        return format(int(value), ",")
    if operation == "percent2":
        fraction = Fraction(value) * 100
        with localcontext() as context:
            context.prec = 80
            return format(
                Decimal(fraction.numerator) / Decimal(fraction.denominator), ".2f"
            )
    if operation == "join":
        return ", ".join(value)
    if operation == "sum":
        return str(int(value)) if value.denominator == 1 else str(value)
    return str(value)


def main():
    n = 0

    def require(ok, label):
        nonlocal n
        assert ok, label
        n += 1

    pdf = PdfReader(ROOT / "paper/manuscript.pdf")
    require(len(pdf.pages) == 6, "six current manuscript pages")
    pages = [unicodedata.normalize("NFKC", p.extract_text() or "") for p in pdf.pages]
    compact = re.sub(r"\s+", " ", "\n".join(pages))
    words = re.sub(r"([A-Za-z])-\s+([A-Za-z])", r"\1\2", "\n".join(pages))
    words = re.sub(r"\s+", " ", words)
    tex = (ROOT / "paper/main.tex").read_text(encoding="utf-8")
    bindings = load("paper/bindings.json")
    require(
        len(bindings) == 158 and len({b["name"] for b in bindings}) == 158,
        "158 unique actual used bindings",
    )
    for binding in bindings:
        value = expected(binding)
        require(value == binding["display"], "independent source value/format")
        require(
            "\\newcommand{\\" + binding["name"] + "}{" + value + "}" in tex,
            "actual bound TeX definition",
        )
        require(
            len(re.findall(r"\\" + re.escape(binding["name"]) + r"\b", tex)) >= 2,
            "macro actually used beyond definition",
        )
        require(value in compact, "actual PDF source value present")
    table = re.sub(r"\s+", " ", pages[1])
    for row in load("results/case_accounts.csv"):
        parts = [
            row["case"],
            row["window_actions"],
            row["zero_actions"],
            row["negative_actions"],
            format(Decimal(row["net_usd"]), ",.2f"),
            format(Decimal(row["gross_absolute_usd"]), ",.2f"),
        ]
        ratio = Fraction(row["net_offset_fraction"]) * 100
        with localcontext() as context:
            context.prec = 80
            parts.append(
                format(Decimal(ratio.numerator) / Decimal(ratio.denominator), ".2f")
                + "%"
            )
        require(" ".join(parts) in table, "complete actual PDF case table row")
    for phrase in [
        "Not peer reviewed",
        "remains unexecuted",
        "not a random or national sample",
        "not an immutable historical snapshot",
        "not outlays or paid cash",
        "not automatically a distinct legal modification",
        "not validated staffing capacity",
        "source informed, not blinded",
        "Source values were visible",
        "not atomicity",
        "Calendar dates cannot order records on the same day",
        "No negative value was clamped or omitted",
        "No verified task identity",
        "Azure optimization",
        "Treasury does not endorse",
    ]:
        require(
            phrase.lower() in words.lower(),
            ("actual source/measurement qualification", phrase),
        )
    require(len(load("PLAN_FREEZE.json")["hashes"]) == 24, "actual freeze dependencies")
    verification = load("results/verification.json")
    require(verification["authored_fixture_methods"] == 33, "current authored fixtures")
    for name, digest in verification["result_sha256"].items():
        require(
            hashlib.sha256((ROOT / "results" / name).read_bytes()).hexdigest()
            == digest,
            "current result hashes",
        )
    for suffix in ["310", "312"]:
        replay = load("results/reproduction_cpython" + suffix + ".json")
        require(
            replay["status"] == "PASS" and replay["full_history"],
            "isolated full history replay",
        )
        require(
            len(replay["reproduced_files"]) == 6
            and replay["unchanged_source_files"] == 9,
            "exact replay scope",
        )
        require(
            replay["reproduced_files"] == list(verification["result_sha256"]),
            "six current outputs",
        )
    scope = load("paper/PUBLICATION_SCOPE.json")
    require(
        scope["scope"] == "independent-program-study"
        and scope["formal_submission_target"] is False,
        "independent manuscript scope",
    )
    require(len(scope["public_files"]) == 5, "five approved paper files")
    for name, digest in scope["public_files"].items():
        require(
            hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest,
            "current scoped bytes",
        )
    for name in ["counts_and_obligations", "signed_offsets", "fixed_window_counts"]:
        require(
            (ROOT / "figures" / (name + ".pdf")).read_bytes()
            == (ROOT / "paper/images" / (name + ".pdf")).read_bytes(),
            "current figure PDF copy",
        )
    visual = load("paper/visual_review.json")
    require(
        visual["pages_reviewed"] == [1, 2, 3, 4, 5, 6], "all current pages reviewed"
    )
    require(
        visual["manuscript_sha256"]
        == hashlib.sha256((ROOT / "paper/manuscript.pdf").read_bytes()).hexdigest(),
        "actual reviewed PDF version",
    )
    for name, digest in visual["reviewed_figure_png_sha256"].items():
        require(
            hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest,
            "reviewed current figure bytes",
        )
    receipt = dict(
        status="PASS",
        finite_conditions=n,
        used_numeric_bindings=len(bindings),
        pages=len(pdf.pages),
        scope_files=5,
        scope="Actual used source bindings, complete PDF table rows, source/measurement limits, two replay receipts, current result/figure hashes and reviewed independent scope. Finite evidence, not universal correctness.",
    )
    (ROOT / "paper/verification.json").write_bytes(
        (json.dumps(receipt, indent=2) + "\n").encode()
    )
    print(json.dumps(receipt))


if __name__ == "__main__":
    main()
