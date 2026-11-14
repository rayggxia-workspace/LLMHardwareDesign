"""Estimate short-workload sensitivity using native per-wave A/B timing ratios."""

import argparse
from collections import defaultdict
from fractions import Fraction
import json
from pathlib import Path


def wave_ratios(comparison):
    ratios = defaultdict(list)
    for page in comparison["waves_by_page"].values():
        for index, row in page.items():
            ratios[int(index)].append(Fraction(row["candidate_cycles"], row["baseline_cycles"]))
    return {i: sum(values) / len(values) for i, values in ratios.items()}


def extrapolate(root, mode, ratios):
    audit = json.loads((root / "timing-audit.json").read_bytes())
    if mode == "decode":
        a, b = audit["retirement_ps"]
        window, count = b - a, 1
    else:
        window, count = audit["elapsed_ps"], 2

    samples = defaultdict(list)
    with (root / "ffn-weight-timing.jsonl").open(encoding="ascii") as source:
        for line in source:
            row = json.loads(line)
            phase = row["step"] if mode == "decode" else row["page"] // 289 + 1
            if mode == "decode" and phase != 2:
                continue
            if len(samples[phase]) == 4:
                continue
            batches = row["batches"]
            if len(batches) != 64:
                raise ValueError("expected 64 FFN calls and waits")
            delta = 0
            previous_wait = 0
            for index, batch in enumerate(batches):
                start = min(p["start_ps"] for p in batch["projections"])
                end = batch["wait_end_ps"]
                if not previous_wait <= start < end:
                    raise ValueError("overlapping FFN wait windows")
                previous_wait = end
                delta += (end - start) * (ratios[index] - 1)
            samples[phase].append(delta)
    if len(samples) != count or any(len(v) != 4 for v in samples.values()):
        raise ValueError("four FFN layers per measured phase required")
    delta = 36 * sum(sum(rows) / len(rows) for rows in samples.values())
    return dict(
        baseline_tok_s=count * 1e12 / window,
        projected_tok_s=count * 1e12 / float(window + delta),
        baseline_window_ps=window,
        projected_extra_ps=float(delta),
        first_four_layer_delta_ps={p: [float(v) for v in rows] for p, rows in samples.items()},
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("native_comparison", type=Path)
    parser.add_argument("decode", type=Path)
    parser.add_argument("prefill", type=Path)
    args = parser.parse_args()
    comparison = json.loads(args.native_comparison.read_bytes())
    ratios = wave_ratios(comparison)
    if comparison["partial"] or sorted(ratios) != list(range(64)):
        raise ValueError("native comparison must include two full FFN pages")
    print(json.dumps({
        "method": "Apply matched native WAIT-window ratios to the first four TLM FFN layers per phase; scale to 36 layers. DDR scheduling is frozen.",
        "decode": extrapolate(args.decode, "decode", ratios),
        "prefill": extrapolate(args.prefill, "prefill", ratios),
    }, indent=2))


if __name__ == "__main__":
    main()
