"""Write an independent manuscript with actual used bindings to complete saved evidence."""

from pathlib import Path
from decimal import Decimal, localcontext
from fractions import Fraction
import csv, hashlib, json, shutil

ROOT = Path(__file__).resolve().parents[1]
bindings = []


def letters(index):
    result = ""
    while True:
        result = chr(65 + index % 26) + result
        index = index // 26 - 1
        if index < 0:
            return result


def data(file):
    if file.endswith(".csv"):
        with (ROOT / file).open(encoding="utf-8", newline="") as f:
            return list(csv.DictReader(f))
    return json.loads((ROOT / file).read_bytes())


def bind(file, field=None, query=None, operation="value"):
    value = data(file)
    if query is not None:
        matches = [r for r in value if all(r[k] == v for k, v in query.items())]
        assert len(matches) == 1
        value = matches[0]
    if operation == "sum":
        value = sum((Fraction(r[field]) for r in value), Fraction())
    else:
        for key in field or []:
            value = value[key]
        if operation == "length":
            value = len(value)
    if operation == "money2":
        display = format(Decimal(value), ",.2f")
    elif operation == "commas":
        display = format(int(value), ",")
    elif operation == "percent2":
        exact = Fraction(value) * 100
        with localcontext() as context:
            context.prec = 80
            display = format(
                Decimal(exact.numerator) / Decimal(exact.denominator), ".2f"
            )
    elif operation == "join":
        display = ", ".join(value)
    elif operation == "sum":
        display = str(int(value)) if value.denominator == 1 else str(value)
    else:
        display = str(value)
    name = "Bound" + letters(len(bindings))
    bindings.append(
        dict(
            name=name,
            file=file,
            field=field,
            query=query,
            operation=operation,
            display=display,
        )
    )
    return "\\" + name + "{}"


def summary(*field):
    return bind("results/summary.json", list(field))


def metric(field):
    return bind("results/verification.json", [field], operation="commas")


def case_value(case, field, op="value"):
    return bind("results/case_accounts.csv", [field], dict(case=case), op)


cases = data("data/cases.json")
accounts = data("results/case_accounts.csv")
case_table = []
for row in accounts:
    key = row["case"]
    case_table.append(
        " & ".join(
            [
                key,
                case_value(key, "window_actions"),
                case_value(key, "zero_actions"),
                case_value(key, "negative_actions"),
                case_value(key, "net_usd", "money2"),
                case_value(key, "gross_absolute_usd", "money2"),
                case_value(key, "net_offset_fraction", "percent2") + r"\%",
            ]
        )
        + r" \\"
    )
p1 = (
    r"""\documentclass[11pt,letterpaper]{article}
\usepackage[margin=0.72in]{geometry}
\usepackage[T1]{fontenc}
\usepackage{lmodern,microtype,booktabs,array,graphicx,pdflscape,xcolor,amsmath,hyperref}
\hypersetup{colorlinks=true,urlcolor=blue,linkcolor=blue,pdftitle={Count contract actions before treating dollars as administrative activity}}
\setlength{\parindent}{0pt}
\setlength{\parskip}{6pt}
\newcommand{\heading}[1]{\vspace{5pt}{\large\bfseries #1}\par}
%%BINDINGS%%
\begin{document}
{\LARGE\bfseries Count contract actions before treating dollars as administrative activity\par}
\vspace{4pt}
Independent research program \hfill 31 October 2026 UTC\\
\textit{Not peer reviewed. Current source view; retrospective accounting.}

\heading{Decision and practical finding}
A contract review queue built from net obligations answers a different question from one built from transaction counts. In the fixed convenience cohort of """
    + summary("cases")
    + r""" NASA contracts, the two five-contract queues share """
    + summary("queues", "overlap_count")
    + r""" cases. Their union contains """
    + summary("queues", "union_count")
    + r""" cases and their Jaccard ratio is """
    + summary("queues", "jaccard_fraction")
    + r""".

The declared follow-up contains """
    + summary("window_actions")
    + r""" current source transaction records, including """
    + summary("zero_amount_actions")
    + r""" zero-dollar actions and """
    + summary("negative_amount_actions")
    + r""" negative obligations. These records would not all be visible in a positive-dollar-only activity measure. This does not measure staff hours, contract quality or vendor risk.

\begin{tabular}{@{}p{1.38in}p{5.15in}@{}}
\toprule
Count-based queue & """
    + bind("results/summary.json", ["queues", "action_count_queue"], operation="join")
    + r"""\\
Net-obligation queue & """
    + bind("results/summary.json", ["queues", "net_obligation_queue"], operation="join")
    + r"""\\
\bottomrule
\end{tabular}

\heading{Recommended use}
Keep source-action counts, zero and signed adjustments, gross obligations and net obligations side by side. A dollar total is a financial measure; the recorded action count is an activity proxy. Neither establishes the effort required to review a contract. Before using these measures for staffing, collect task definitions, review times and prospective service outcomes. The five-case capacity here is an authored illustration, not validated staffing capacity.

\heading{Fixed scope and timing}
The protocol selected the first ascending-Award-ID API page of """
    + summary("cases")
    + r""" NASA prime contracts with a current base-obligation assertion in calendar 2024. No dollar or recipient filter selected cases. All returned cases were retained; the source search was repeated unchanged. For each contract, before/after transaction counts agreed with the complete bounded response.

The private capture contains """
    + summary("native_records")
    + r""" current records across """
    + bind("data/capture_manifest.json", ["requests"], operation="length")
    + r""" native responses. Follow-up includes source-calendar day 0 through 364 relative to the current Base Obligation Date assertion. Day 365 is excluded. Full follow-up had elapsed before capture. This is not an immutable historical snapshot, a live arrival curve or proof of pre-award feature availability.

\heading{Original proposal remains unexecuted}
The original Study 11 pre-award modification classifier remains unexecuted. Official source disclosure describes publication after contract actions, with explicit delay exceptions. Current action dates do not establish when a forecaster could first access the fields. This separate post-award study preserves that hold.
\newpage
"""
)
p2 = (
    r"""{\Large\bfseries Complete case accounting\par}
The """
    + summary("financially_complete_cases")
    + r""" jointly eligible cases retain all fixed follow-up accounts. Amounts below are reported signed USD obligations in the current source, not outlays or paid cash. A source record is not automatically a distinct legal modification or staff task.

{\small
\setlength{\tabcolsep}{5pt}
\begin{tabular}{@{}lrrrrrr@{}}
\toprule
Case & Actions & Zero & Negative & Net USD & Gross absolute USD & Offset\\
\midrule
"""
    + "\n".join(case_table)
    + r"""
\bottomrule
\end{tabular}
}

\heading{Interpretation and complete exclusions}
All """
    + summary("native_records")
    + r""" source rows are classified: """
    + summary("window_actions")
    + r""" are inside the declared window and """
    + bind("results/case_accounts.csv", "at_or_after_horizon_records", operation="sum")
    + r""" are on or after its endpoint. The captured cohort has """
    + bind("results/case_accounts.csv", "missing_key_records", operation="sum")
    + r""" missing-key records, """
    + bind("results/case_accounts.csv", "duplicate_key_records", operation="sum")
    + r""" duplicate-key records, """
    + bind("results/case_accounts.csv", "unknown_date_records", operation="sum")
    + r""" unknown-date records and """
    + summary("unknown_amount_actions")
    + r""" unknown in-window monetary values. These observed zeros do not guarantee such problems are absent from other cohorts.

For complete nonempty windows, gross absolute obligations sum absolute signed amounts. The net-offset fraction is
\[
 \frac{\text{gross absolute obligations}-|\text{net obligations}|}
 {\text{gross absolute obligations}}.
\]
It is unavailable when gross is zero or money/window eligibility is incomplete. This is signed accounting algebra, not waste, savings, recovery or a processing-cost estimate.

C02 has """
    + case_value("C02", "negative_actions")
    + r""" negative action and an offset fraction of """
    + case_value("C02", "net_offset_fraction", "percent2")
    + r"""\%; C08 has """
    + case_value("C08", "negative_actions")
    + r""" negative actions and """
    + case_value("C08", "net_offset_fraction", "percent2")
    + r"""\% offset. No negative value was clamped or omitted. Source modification tokens remain opaque labels; calendar dates cannot order records on the same day. Complete row classifications, all queue ranks and all """
    + bind("results/cumulative_probes.csv", operation="length")
    + r""" fixed cumulative probes remain in the repository.
\newpage
"""
)
p3 = (
    r"""{\Large\bfseries Verification, implementation and limits\par}

\heading{Independent checks and chronology}
Native JSON numeric tokens, identity and current source controls pass """
    + metric("native_source_conditions")
    + r""" finite conditions. Saved native-bound projections pass """
    + metric("saved_source_conditions")
    + r""". A separate dateutil/SQLite/exact-Fraction checker reconstructs every case, row classification, horizon probe, rank and request in """
    + metric("independent_accounting_conditions")
    + r""" conditions without importing the production accounting functions.

The committed freeze binds """
    + bind("PLAN_FREEZE.json", ["hashes"], operation="length")
    + r""" actual source/method dependencies before accounting and queue comparisons. Source values were visible during capture and reconciliation; this was source informed, not blinded. The """
    + metric("authored_fixture_methods")
    + r""" authored fixture methods cover complete duplicate-group quarantine, signed and unavailable money, same-day ambiguity, leap-year/window boundaries, exact high-precision arithmetic, ties and unsupported conversions.

Separate full-history CPython """
    + bind("results/reproduction_cpython310.json", ["python"])
    + r""" and """
    + bind("results/reproduction_cpython312.json", ["python"])
    + r""" replays reproduce """
    + bind(
        "results/reproduction_cpython310.json", ["reproduced_files"], operation="length"
    )
    + r""" outputs exactly and preserve """
    + bind("results/reproduction_cpython310.json", ["unchanged_source_files"])
    + r""" source files each. Figure checks bind """
    + bind("figures/verification.json", ["source_bound_artists"])
    + r""" source artists and """
    + bind("figures/verification.json", ["svg_coordinate_conditions"])
    + r""" actual SVG coordinate conditions. Finite checks do not establish universal correctness.

\heading{Runnable implementation exercise}
The seven complete requests retain two qualified current accounts and reject five unsupported conversions. C01 returns """
    + bind("results/exercise.json", [0, "result", "value"])
    + r""" eligible current transaction records; C03 returns USD """
    + bind("results/exercise.json", [1, "result", "value"], operation="money2")
    + r""" in signed obligations. Unsupported requests seek staff hours, vendor risk, pre-award features, a dollars-to-action conversion or future modifications. The local interface rejects each. An acceptance is a scoped data-description result, not an endorsement of source truth or production readiness.

Run the saved-data replay in a new directory:
\begin{verbatim}
python -m pip install -r requirements.txt
python src/replay.py --out ../contract-accounting-replay
\end{verbatim}

\heading{Material limits and next evidence}
This bounded current API page is a convenience cohort from one agency and one base year. It is not a random or national sample. Current histories can be revised; count agreement is not atomicity, original delivery or complete historical reporting. No verified task identity, staff-hour estimate, vendor score, classifier accuracy, causal effect, production deployment or realized saving is claimed. A staffing follow-up needs measured review work; a pre-award model needs verified feature snapshots and protected labels at its prediction origin.

Only minimal public government transaction facts and independent aggregates are included. Native narratives, recipient information and source PDFs remain private. Separate formal-publication projects, including Azure optimization, remain private.

{\small Sources: U.S. Department of the Treasury, USAspending.gov.
\url{https://api.usaspending.gov/};
\url{https://www.usaspending.gov/data/about-the-data-download.pdf}.
Endpoint contracts and exact request/hash manifests are retained in the repository. Treasury does not endorse this independent analysis. Original code uses MIT; agency facts are attributed separately.}
"""
)
pages = []
for title, name in [
    ("Current records and obligations", "counts_and_obligations"),
    ("Signed financial offsets", "signed_offsets"),
    ("Fixed calendar-window probes", "fixed_window_counts"),
]:
    pages.append(
        r"\begin{landscape}"
        + "\n"
        + r"{\large\bfseries "
        + title
        + r"\par}"
        + "\n"
        + r"\vspace{3pt}"
        + "\n"
        + r"\begin{center}\includegraphics[width=9.45in,height=6.20in,keepaspectratio]{images/"
        + name
        + r".pdf}\end{center}"
        + "\n"
        + r"\end{landscape}"
        + "\n"
    )
tex = p1 + p2 + p3 + "\n" + "".join(pages) + r"\end{document}" + "\n"
definitions = "\n".join(
    "\\newcommand{\\" + b["name"] + "}{" + b["display"] + "}" for b in bindings
)
tex = tex.replace("%%BINDINGS%%", definitions)
paper = ROOT / "paper"
(paper / "images").mkdir(exist_ok=True)
for name in ["counts_and_obligations", "signed_offsets", "fixed_window_counts"]:
    shutil.copy2(ROOT / "figures" / (name + ".pdf"), paper / "images" / (name + ".pdf"))
(paper / "main.tex").write_bytes(tex.rstrip().encode() + b"\n")
(paper / "bindings.json").write_bytes((json.dumps(bindings, indent=2) + "\n").encode())
print("SOURCE_BOUND_MANUSCRIPT_WRITTEN", len(bindings))
