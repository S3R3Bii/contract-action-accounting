"""Build complete, source-bound case figures with explicit units and zero baselines."""

from pathlib import Path
from fractions import Fraction
import csv, hashlib, json
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def read(name):
    with (ROOT / name).open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def main():
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 10,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "svg.fonttype": "none",
            "svg.hashsalt": "contract-action-accounting",
        }
    )
    accounts = read("results/case_accounts.csv")
    probes = read("results/cumulative_probes.csv")
    folder = ROOT / "figures"
    folder.mkdir(exist_ok=True)
    entries = []
    colors = ["#177f83", "#db8f24", "#5959ad"]

    def bars(ax, values, cases, gid_prefix, color, labels):
        y = np.arange(len(cases))
        artists = ax.barh(y, values, color=color, height=0.65)
        ax.set_yticks(y, cases)
        ax.invert_yaxis()
        ax.set_xlim(left=0)
        ax.grid(axis="x", alpha=0.18)
        ax.set_axisbelow(True)
        upper = max(values, default=0)
        ax.set_xlim(0, upper * 1.22 if upper > 0 else 1)
        result = []
        for i, (artist, value, case, label) in enumerate(
            zip(artists, values, cases, labels)
        ):
            gid = gid_prefix + "-" + case
            artist.set_gid(gid)
            ax.text(
                value + max(upper * 0.015, 0.003), i, label, va="center", fontsize=10
            )
            result.append(
                dict(
                    gid=gid,
                    case=case,
                    value=float(value),
                    label=label,
                    y_center=float(i),
                    height=0.65,
                )
            )
        return result

    def finish(fig, name, artists, axes):
        fig.savefig(folder / (name + ".png"), dpi=160, facecolor="white")
        fig.savefig(
            folder / (name + ".svg"), facecolor="white", metadata={"Date": None}
        )
        fig.savefig(
            folder / (name + ".pdf"),
            facecolor="white",
            metadata={"CreationDate": None, "ModDate": None},
        )
        svg = folder / (name + ".svg")
        svg.write_bytes(
            (
                "\n".join(
                    line.rstrip()
                    for line in svg.read_text(encoding="utf-8").splitlines()
                )
                + "\n"
            ).encode()
        )
        fig.canvas.draw()
        dimensions = fig.get_size_inches() * 72
        records = []
        for artist_record, ax in zip(artists, axes):
            bbox = ax.get_position()
            artist_record["axis_points"] = dict(
                left=float(bbox.x0 * dimensions[0]),
                top=float((1 - bbox.y1) * dimensions[1]),
                width=float(bbox.width * dimensions[0]),
                height=float(bbox.height * dimensions[1]),
                xlim=list(map(float, ax.get_xlim())),
                ylim=list(map(float, ax.get_ylim())),
            )
            records.append(artist_record)
        entries.append(
            dict(
                name=name,
                artists=records,
                asset_sha256={
                    ext: hashlib.sha256(
                        (folder / (name + "." + ext)).read_bytes()
                    ).hexdigest()
                    for ext in ["svg", "png", "pdf"]
                },
            )
        )
        plt.close(fig)

    cases = [r["case"] for r in accounts]
    fig, axes = plt.subplots(1, 2, figsize=(11, 8), gridspec_kw={"wspace": 0.35})
    fig.subplots_adjust(left=0.07, right=0.94, bottom=0.11, top=0.86)
    fig.suptitle(
        "Different measures can produce different contract review queues",
        fontsize=15,
        x=0.07,
        ha="left",
        y=0.965,
    )
    fig.text(
        0.07,
        0.913,
        "All 20 fixed cases; the 365-day window uses one current source view",
        fontsize=10,
        color="#444444",
    )
    counts = [int(r["window_actions"]) for r in accounts]
    money = [
        float(Fraction(r["net_usd"]) / 1000000) if r["money_complete"] == "True" else 0
        for r in accounts
    ]
    items = bars(axes[0], counts, cases, "count", colors[0], [str(x) for x in counts])
    more = bars(
        axes[1],
        money,
        cases,
        "net",
        colors[1],
        [
            format(x, ".3f") if r["money_complete"] == "True" else "unavailable"
            for x, r in zip(money, accounts)
        ],
    )
    axes[0].set_title("Current transaction records")
    axes[0].set_xlabel("Eligible action records")
    axes[0].xaxis.set_major_locator(MaxNLocator(integer=True))
    axes[1].set_title("Net reported obligations")
    axes[1].set_xlabel("USD millions, signed net obligations")
    fig.text(
        0.07,
        0.025,
        "Counts are not staff hours. Obligations are not outlays. Case IDs retain the fixed source-page order.",
        fontsize=9,
        color="#444444",
    )
    finish(fig, "counts_and_obligations", items + more, [axes[0]] * 20 + [axes[1]] * 20)
    values = [
        (
            float(Fraction(r["net_offset_fraction"]) * 100)
            if r["net_offset_fraction"]
            else 0
        )
        for r in accounts
    ]
    fig, ax = plt.subplots(figsize=(9, 8))
    fig.subplots_adjust(left=0.10, right=0.90, bottom=0.12, top=0.85)
    fig.suptitle(
        "Signed adjustments can offset gross recorded obligations",
        fontsize=15,
        x=0.10,
        ha="left",
        y=0.965,
    )
    fig.text(
        0.10,
        0.912,
        "Net-offset fraction = (gross absolute obligations - |net obligations|) / gross absolute obligations",
        fontsize=9,
    )
    items = bars(
        ax,
        values,
        cases,
        "offset",
        colors[2],
        [
            format(v, ".2f") + "%" if r["net_offset_fraction"] else "unavailable"
            for v, r in zip(values, accounts)
        ],
    )
    ax.set_xlim(0, 100)
    ax.set_xlabel("Percent of gross absolute obligations offset within each case")
    fig.text(
        0.10,
        0.025,
        "All 20 cases retained. Zero offset is visible as a 0.00% label. This is accounting algebra, not waste or savings.",
        fontsize=9,
        color="#444444",
    )
    finish(fig, "signed_offsets", items, [ax] * 20)
    fig, axes = plt.subplots(1, 3, figsize=(11, 8), gridspec_kw={"wspace": 0.38})
    fig.subplots_adjust(left=0.07, right=0.95, bottom=0.12, top=0.85)
    fig.suptitle(
        "Action counts depend on the declared calendar window",
        fontsize=15,
        x=0.07,
        ha="left",
        y=0.965,
    )
    fig.text(
        0.07,
        0.912,
        "Every case and all three fixed horizons; records on the horizon day are excluded",
        fontsize=10,
    )
    items = []
    artist_axes = []
    maximum = max(int(r["window_actions"]) for r in probes)
    for j, horizon in enumerate([30, 90, 365]):
        ax = axes[j]
        values = [
            next(
                int(r["window_actions"])
                for r in probes
                if r["case"] == case and int(r["horizon_days"]) == horizon
            )
            for case in cases
        ]
        records = bars(
            ax,
            values,
            cases,
            "probe-" + str(horizon),
            colors[j],
            [str(v) for v in values],
        )
        for record in records:
            record["horizon_days"] = horizon
        items += records
        artist_axes += [ax] * len(records)
        ax.set_title(str(horizon) + " days")
        ax.set_xlim(0, maximum * 1.20)
        ax.set_xlabel("Source action records")
        ax.xaxis.set_major_locator(MaxNLocator(integer=True))
    fig.text(
        0.07,
        0.025,
        "Current source view from asserted base date; not original publication, staff hours or a live arrival curve.",
        fontsize=9,
        color="#444444",
    )
    finish(fig, "fixed_window_counts", items, artist_axes)
    (folder / "manifest.json").write_bytes(
        (json.dumps(entries, indent=2) + "\n").encode()
    )
    print("FIGURES_PRODUCED", len(entries), sum(len(r["artists"]) for r in entries))


if __name__ == "__main__":
    main()
