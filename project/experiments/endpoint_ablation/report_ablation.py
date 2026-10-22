"""Derived plotting only; raw routing and imported witnesses remain distinct."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from study import ARMS


def main():
    p = argparse.ArgumentParser()
    p.add_argument("run", type=Path)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    if a.out.exists():
        raise SystemExit("Choose a new figure directory")
    a.out.mkdir(parents=True)
    rows = [json.loads(line) for path in sorted(a.run.glob("*-cases.jsonl"))
            for line in path.read_text(encoding="utf-8").splitlines()]
    fields = ["routed", "known_feasible_heuristic_miss", "proven_no_path_fixed_mapping", "unknown"]
    table = []
    for arm in ARMS:
        subset = [r for r in rows if r["arm"] == arm]
        table.append({"arm": arm, "total": len(subset), **{
            f: sum(r["knowledge"] == f for r in subset) for f in fields}})
    with (a.out / "routing-summary.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["arm", "total", *fields], lineterminator="\n")
        writer.writeheader()
        writer.writerows(table)
    markdown = "| arm | raw routed | imported witness only | proven no path | unknown |\n|---|---:|---:|---:|---:|\n"
    markdown += "".join("| " + row["arm"] + " | " + " | ".join(str(row[k]) for k in fields) + " |\n" for row in table)
    (a.out / "table.md").write_bytes(markdown.encode())
    fig, ax = plt.subplots(figsize=(10, 4.5))
    offsets = [0] * len(ARMS)
    labels = ["Router found", "Imported legal witness", "Fixed mapping: no path", "Unknown"]
    colors = ["#247ba0", "#70c1b3", "#d9a441", "#d6dce4"]
    for field, label, color in zip(fields, labels, colors):
        values = [r[field] for r in table]
        ax.barh(ARMS, values, left=offsets, label=label, color=color)
        for i, (left, value) in enumerate(zip(offsets, values)):
            if value >= 4:
                ax.text(left + value / 2, i, str(value), ha="center", va="center", fontsize=10)
        offsets = [left + value for left, value in zip(offsets, values)]
    ax.invert_yaxis()
    ax.set_xlabel("Paired cases per condition (same mapping and 14 routing attempts)")
    ax.set_title("Synthetic endpoint restrictions: evidence status, not physical PPA")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=2, frameon=False)
    fig.tight_layout()
    for extension in ("svg", "png"):
        fig.savefig(a.out / ("routing-success." + extension), dpi=160, metadata={"Creator": "endpoint_ablation/report_ablation.py"})
    plt.close(fig)
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    manifest = {"input_manifest_sha256": sha(a.run / "manifest.json"),
                "plotter_sha256": sha(Path(__file__)), "matplotlib": matplotlib.__version__,
                "files": {f.name: sha(f) for f in sorted(a.out.iterdir()) if f.is_file()}}
    (a.out / "report-manifest.json").write_bytes((json.dumps(manifest, indent=2) + "\n").encode())
    print(markdown)


if __name__ == "__main__":
    main()
