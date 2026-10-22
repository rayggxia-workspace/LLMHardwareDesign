"""Generate manuscript-useful summaries from frozen raw evidence, not hand values."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def main():
    p = argparse.ArgumentParser()
    p.add_argument("run_dir", type=Path)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    if a.out.exists():
        raise SystemExit("Choose a new report directory")
    a.out.mkdir(parents=True)
    rows = [json.loads(line) for f in sorted(a.run_dir.glob("*-cases.jsonl"))
            for line in f.read_text(encoding="utf-8").splitlines()]
    variants = sorted({r["variant"] for r in rows})
    multi_budget = sorted({r["route_attempt_budget"] for r in rows if r["method"] == "multi_order"})
    methods = ["sequential", "multi_order"]
    table = []
    for variant in variants:
        record = {"variant": variant}
        for method in methods:
            selected = [r for r in rows if r["variant"] == variant and r["method"] == method]
            ok = [r for r in selected if r["status"] == "routed"]
            record[method+"_routed"] = len(ok)
            record[method+"_total"] = len(selected)
            record[method+"_runtime_seconds"] = sum(r["runtime_seconds"] for r in selected)
            record[method+"_mean_cost_success_only"] = (sum(r["validation"]["custom_cost_units"] for r in ok)/len(ok)) if ok else None
        table.append(record)
    with (a.out/"routing-summary.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(table[0]))
        w.writeheader()
        w.writerows(table)
    plt.rcParams.update({"font.size": 10, "svg.fonttype": "none"})
    fig, ax = plt.subplots(figsize=(10, 4.5), layout="constrained")
    x = list(range(len(variants)))
    for offset, method, color, label in [(-0.18, "sequential", "#8b9bb0", "Sequential (1 order)"),
                                         (0.18, "multi_order", "#216c9c", f"Multi-order ({'/'.join(map(str, multi_budget))} trials)")]:
        y = [100*r[method+"_routed"]/r[method+"_total"] for r in table]
        ax.bar([v+offset for v in x], y, width=0.34, color=color, label=label)
    ax.set(xticks=x, xticklabels=variants, ylabel="Legally routed cases (%)", ylim=(0, 105),
           title="Frozen passive fabric: abstract routing only, no PPA inference")
    ax.tick_params(axis="x", labelrotation=25)
    ax.legend(frameon=False)
    ax.grid(axis="y", alpha=0.2)
    ax.set_axisbelow(True)
    fig.savefig(a.out/"routing-success.svg")
    fig.savefig(a.out/"routing-success.png", dpi=160)
    plt.close(fig)
    lines = ["| Variant | Sequential | Multi-order |", "|---|---:|---:|"]
    lines += [f"| {r['variant']} | {r['sequential_routed']}/{r['sequential_total']} | {r['multi_order_routed']}/{r['multi_order_total']} |" for r in table]
    (a.out/"table.md").write_text("\n".join(lines)+"\n", encoding="utf-8")
    receipt = {"source_manifest_sha256": hashlib.sha256((a.run_dir/"manifest.json").read_bytes()).hexdigest(),
               "matplotlib": matplotlib.__version__,
               "report_source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
               "files": {f.name: hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(a.out.iterdir())}}
    (a.out/"report-manifest.json").write_text(json.dumps(receipt, indent=2)+"\n", encoding="utf-8")
    print(json.dumps({"variants": len(table), "out": str(a.out)}))


if __name__ == "__main__":
    main()
