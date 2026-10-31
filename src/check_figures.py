"""Check actual SVG geometry and labels against independently read complete source results."""

from pathlib import Path
from fractions import Fraction
import csv, hashlib, json, re, xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


def read(name):
    with (ROOT / name).open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def main():
    n = 0
    coordinate_checks = 0

    def require(ok, label):
        nonlocal n
        assert ok, label
        n += 1

    accounts = {r["case"]: r for r in read("results/case_accounts.csv")}
    probes = {
        (r["case"], int(r["horizon_days"])): int(r["window_actions"])
        for r in read("results/cumulative_probes.csv")
    }
    manifest = json.loads((ROOT / "figures/manifest.json").read_bytes())
    require(len(manifest) == 3, "three complete figures")
    seen = set()
    for figure in manifest:
        svg = (ROOT / "figures" / (figure["name"] + ".svg")).read_bytes()
        tree = ET.fromstring(svg)
        groups = {x.attrib.get("id"): x for x in tree.iter() if x.tag.endswith("g")}
        texts = [
            "".join(x.itertext()).strip() for x in tree.iter() if x.tag.endswith("text")
        ]
        for extension, digest in figure["asset_sha256"].items():
            require(
                hashlib.sha256(
                    (ROOT / "figures" / (figure["name"] + "." + extension)).read_bytes()
                ).hexdigest()
                == digest,
                "current figure bytes",
            )
        for artist in figure["artists"]:
            gid = artist["gid"]
            case = artist["case"]
            require(gid not in seen, "unique actual artist")
            seen.add(gid)
            row = accounts[case]
            if gid.startswith("count-"):
                value = Fraction(row["window_actions"])
                label = str(int(value))
            elif gid.startswith("net-"):
                value = Fraction(row["net_usd"]) / 1000000
                label = format(float(value), ".3f")
            elif gid.startswith("offset-"):
                value = Fraction(row["net_offset_fraction"]) * 100
                label = format(float(value), ".2f") + "%"
            else:
                value = Fraction(probes[(case, artist["horizon_days"])])
                label = str(int(value))
            require(
                abs(artist["value"] - float(value)) < 1e-12,
                "independent displayed source value",
            )
            require(
                artist["label"] == label and label in texts, "actual SVG numeric label"
            )
            require(case in texts, "every case label present")
            group = groups[gid]
            paths = [x for x in group.iter() if x.tag.endswith("path")]
            require(len(paths) == 1, "actual bar path")
            coordinates = list(
                map(
                    float,
                    re.findall(
                        r"[-+]?(?:\d*\.)?\d+(?:[eE][-+]?\d+)?", paths[0].attrib["d"]
                    ),
                )
            )
            require(len(coordinates) == 8, "four actual bar corners")
            xs = coordinates[::2]
            ys = coordinates[1::2]
            a = artist["axis_points"]
            lo, hi = a["xlim"]
            zero = a["left"] + (0 - lo) / (hi - lo) * a["width"]
            end = a["left"] + (float(value) - lo) / (hi - lo) * a["width"]
            require(
                abs(min(xs) - min(zero, end)) < 0.02
                and abs(max(xs) - max(zero, end)) < 0.02,
                "actual SVG zero and endpoint",
            )
            coordinate_checks += 2
            top, bottom = a["ylim"]
            center = (
                a["top"] + (artist["y_center"] - bottom) / (top - bottom) * a["height"]
            )
            height = artist["height"] / abs(top - bottom) * a["height"]
            require(
                abs((min(ys) + max(ys)) / 2 - center) < 0.02,
                "actual SVG case/horizon center",
            )
            coordinate_checks += 1
            require(abs(max(ys) - min(ys) - height) < 0.02, "actual SVG bar thickness")
            coordinate_checks += 1
        require(all(case in texts for case in accounts), "no omitted case")
    require(len(seen) == 120, "all 40 count/net,20 offset and60 horizon bars")
    receipt = dict(
        status="PASS",
        finite_conditions=n,
        source_bound_artists=len(seen),
        svg_coordinate_conditions=coordinate_checks,
        asset_hashes=9,
        scope="Actual SVG bars, source-derived values, endpoints, positions and numeric labels for all cases. Visual review recorded separately; no universal or accessibility certification.",
    )
    (ROOT / "figures/verification.json").write_bytes(
        (json.dumps(receipt, indent=2) + "\n").encode()
    )
    print(json.dumps(receipt))


if __name__ == "__main__":
    main()
