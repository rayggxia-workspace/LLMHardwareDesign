"""Check a same-program FFN A/B and attribute the first four layer deltas."""

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path

from compare_att1_selected import load_pages, signature


def read_rows(path):
    with path.open(encoding="ascii") as stream:
        return [json.loads(line) for line in stream if line.endswith("\n")]


def batches_summary(rows):
    summary = defaultdict(Counter)
    for row in rows:
        if len(row["batches"]) != 64:
            raise ValueError("unexpected number of FFN batches")
        for batch in row["batches"]:
            ps = batch["projections"]
            terminal = max(p["terminal_ps"] for p in ps)
            if terminal > batch["wait_end_ps"]:
                raise ValueError("WAIT retired before its final P")
            latest = [p["target"] for p in ps if p["terminal_ps"] == terminal]
            kind = ps[0]["kind"]
            summary[kind]["batches"] += 1
            summary[kind]["tail_ps"] += batch["wait_end_ps"] - terminal
            summary[kind]["latest_" + ",".join(map(str, sorted(latest)))] += 1
            for p in ps:
                for field in ("weight_wait_ps", "weight_beats"):
                    summary[kind][f"P{p['target']}_{field}"] += p[field]
    return summary


def compare(mode, baseline, candidate, anchor_ps):
    def contents(root):
        return (
            load_pages(root / "page-timing.jsonl"),
            {(r["step"], r["page"]): r for r in read_rows(root / "ffn-weight-timing.jsonl")},
            read_rows(root / "ffn-down.sha256.jsonl"),
        )

    (old, metrics_a, hashes_a), (new, metrics_b, hashes_b) = map(contents, (baseline, candidate))
    expected = 582 if mode == "decode" else 578
    if max(len(old), len(new)) > expected:
        raise ValueError("unexpected replay length")
    paired = min(len(old), len(new))
    for a, b in zip(hashes_a, hashes_b):
        if a != b:
            raise ValueError(f"FFN Down contents differ at {a[:2]}")
    samples = defaultdict(list)
    rows_a, rows_b = [], []
    for a, b in zip(old, new):
        if signature(a) != signature(b):
            raise ValueError(f"different executed program at page {a['page']}")
        if any(a["ddr"].get(k, 0) != b["ddr"].get(k, 0) for k in ("reads", "writes", "callbacks")):
            raise ValueError(f"DDR traffic got changed at page {a['page']}")
        counts = [{bank: {k: n for k, n in row.items() if k != "port_wait_ps"}
                   for bank, row in p["sram"].items()} for p in (a, b)]
        if counts[0] != counts[1]:
            raise ValueError(f"S traffic changed at page {a['page']}")
        key = (a["step"], a["page"])
        if (key in metrics_a) != (key in metrics_b):
            raise ValueError(f"unequal FFN trace coverage at {key}")
        if key not in metrics_a:
            continue
        phase = a["step"] if mode == "decode" else 1 + a["page"] // 289
        if len(samples[phase]) < 4:
            rows_a.append(metrics_a[key])
            rows_b.append(metrics_b[key])
            samples[phase].append(dict(page=a["page"], baseline_ps=a["end_ps"] - a["start_ps"],
                                       candidate_ps=b["end_ps"] - b["start_ps"]))
    out = dict(mode=mode, matched_pages=paired, matched_down=min(len(hashes_a), len(hashes_b)),
               samples=samples, baseline_ffn=batches_summary(rows_a), candidate_ffn=batches_summary(rows_b))
    deltas = {p: sum(a["baseline_ps"] - a["candidate_ps"] for a in rows) / 4
              for p, rows in samples.items() if len(rows) == 4}
    completed = len(old) == expected and (baseline / "timing-audit.json").is_file()
    if completed:
        anchor_ps = old[-1]["end_ps"] - (old[290]["end_ps"] if mode == "decode" else 0)
    out["complete_baseline"] = completed
    if 1 in deltas and anchor_ps:
        saved = deltas.get(2, deltas[1]) if mode == "decode" else deltas[1] + deltas.get(2, deltas[1])
        out["baseline_window_ps"] = anchor_ps
        out["predicted_window_ps"] = anchor_ps - 36 * saved
        out["predicted_tok_s"] = (1 if mode == "decode" else 2) * 1e12 / out["predicted_window_ps"]
    if completed and len(new) == expected and (candidate / "timing-audit.json").is_file():
        if len(metrics_a) != 72 or len(metrics_b) != 72 or len(hashes_a) != 72 or hashes_a != hashes_b:
            raise ValueError("incomplete FFN timing or numerical replay")
        a, b = [json.loads((root / "execution.json").read_bytes()) for root in (baseline, candidate)]
        if mode == "decode" and ([r[0] for r in a["retirements"]] != [r[0] for r in b["retirements"]]
                                 or a["kv_cross_step_read_beats"] != b["kv_cross_step_read_beats"]):
            raise ValueError("retirement changed")
        key = "interval_tok_s" if mode == "decode" else "prefill_tokens_per_second"
        out["measured_tok_s"] = {name: json.loads((root / "timing-audit.json").read_bytes())[key]
                                for name, root in (("baseline", baseline), ("candidate", candidate))}
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("decode", "prefill"))
    parser.add_argument("baseline", type=Path)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("--anchor-ps", type=float, default=0)
    args = parser.parse_args()
    print(json.dumps(compare(args.mode, args.baseline, args.candidate, args.anchor_ps), indent=2))


if __name__ == "__main__":
    main()
