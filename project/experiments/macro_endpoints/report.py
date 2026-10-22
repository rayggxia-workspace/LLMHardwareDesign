"""Raw signal RECT centers only; no manufacturing or routing access inference."""
import argparse
from collections import defaultdict
from decimal import Decimal
import json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from common import clean_provenance, file_index, json_bytes, sha


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--run", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    if a.out.exists():
        raise SystemExit("Choose a new task temporary figure directory")
    provenance = clean_provenance(["report.py", "common.py"])
    inventory = json.loads((a.run / "inventory.json").read_bytes())
    summary = json.loads((a.run / "summary.json").read_bytes())
    a.out.mkdir(parents=True)
    fig, axes = plt.subplots(1, len(inventory["macros"]), figsize=(12, 4.5))
    colors = {"metal5": "#6c4aa4", "metal6": "#168a83"}
    for ax, (candidate, entry) in zip(axes, inventory["macros"].items()):
        macro = entry["lef"]["macro"]
        width, height = map(float, macro["size_um"])
        centers = defaultdict(list)
        for pin in macro["pins"]:
            if pin["use"] != "SIGNAL":
                continue
            for port in pin["ports"]:
                for rect in port["rects"]:
                    x0, y0, x1, y1 = map(float, rect["rect_um"])
                    centers[rect["layer"]].append(((x0 + x1) / 2, (y0 + y1) / 2))
        ax.plot([0, width, width, 0, 0], [0, 0, height, height, 0], color="#667080", linewidth=0.8)
        for layer, points in sorted(centers.items()):
            ax.scatter([p[0] for p in points], [p[1] for p in points], s=3,
                       color=colors.get(layer), label=layer, alpha=0.7, rasterized=True)
        ax.set_title(candidate + " / " + str(summary["macros"][candidate]["signal_pins"]) + " signal pins")
        ax.set_xlabel("Raw LEF x (um)")
        ax.set_ylabel("Raw LEF y (um)")
        ax.set_aspect("equal")
        ax.margins(0.06)
        ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=2, frameon=False)
    fig.suptitle("Ordinary LEF signal RECT centers: geometry inventory, not legal-access evidence", fontsize=12)
    fig.text(0.5, 0.015, "Separate macro coordinate frames; no DEF placement. PG and OBS remain in exported data, omitted in this view.",
             ha="center", fontsize=9)
    fig.tight_layout(rect=(0, 0.1, 1, 0.93))
    fig.savefig(a.out / "signal-pin-centers.png", dpi=160)
    fig.savefig(a.out / "signal-pin-centers.svg", metadata={"Creator": "macro_endpoints/report.py"})
    plt.close(fig)
    lines = ["| candidate | size (um) | all pins | SIGNAL | pin RECT | OBS RECT |", "|---|---|---:|---:|---:|---:|"]
    for candidate, row in summary["macros"].items():
        lines.append("| " + candidate + " | " + " x ".join(row["size_um"]) + " | " +
                     " | ".join(str(row[k]) for k in ("total_pins", "signal_pins", "pin_rectangles", "obstruction_rectangles")) + " |")
    (a.out / "table.md").write_bytes(("\n".join(lines) + "\n").encode())
    report = {"input_export_manifest_sha256": sha((a.run / "manifest.json").read_bytes()),
              "provenance": provenance,
              "plotter_source_sha256": sha(Path(__file__).read_bytes()), "matplotlib": matplotlib.__version__,
              "files": file_index(a.out)}
    (a.out / "report-manifest.json").write_bytes(json_bytes(report))
    print("\n".join(lines))


if __name__ == "__main__":
    main()
