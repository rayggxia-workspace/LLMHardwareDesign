"""Audit the same-traffic ATT1 return-credit experiment and extrapolate four layers."""

import argparse
from collections import defaultdict
import json
from pathlib import Path

from compare_att1_selected import attention, load_pages, signature


def analyze(mode, base, candidate, anchor_ps):
    expected = 582 if mode == "decode" else 578
    old, new = (load_pages(root / "page-timing.jsonl") for root in (base, candidate))
    if max(len(old), len(new)) > expected:
        raise ValueError("extra pages")
    samples = defaultdict(list)
    for ref, test in zip(old, new):
        if signature(ref) != signature(test):
            raise ValueError(f"different executed program at page {test['page']}")
        if any(ref["ddr"].get(key, 0) != test["ddr"].get(key, 0)
               for key in ("reads", "writes", "callbacks")):
            raise ValueError(f"DDR traffic differs at page {test['page']}")
        first, second = ({name: {key: count for key, count in totals.items() if key != "port_wait_ps"}
                          for name, totals in row["sram"].items()} for row in (ref, test))
        if first != second:
            raise ValueError(f"SRAM traffic differs at page {test['page']}")
        phase = ref["step"] if mode == "decode" else 1 + ref["page"] // 289
        if attention(ref) and len(samples[phase]) < 4:
            samples[phase].append(dict(page=ref["page"], baseline_ps=ref["end_ps"] - ref["start_ps"],
                                       candidate_ps=test["end_ps"] - test["start_ps"]))
    result = dict(mode=mode, matched_pages=min(len(old), len(new)), samples=dict(samples))
    deltas = {phase: sum(r["baseline_ps"] - r["candidate_ps"] for r in rows) / 4
              for phase, rows in samples.items() if len(rows) == 4}
    tokens = 1 if mode == "decode" else 2
    if len(old) == expected and (base / "timing-audit.json").is_file():
        anchor_ps = old[-1]["end_ps"] - (old[290]["end_ps"] if mode == "decode" else 0)
        result["baseline_complete"] = True
    else:
        result["baseline_complete"] = False
    if 1 in deltas and anchor_ps:
        result["phase_delta_ps_per_layer"] = deltas
        saved = deltas.get(2, deltas[1]) if mode == "decode" else deltas[1] + deltas.get(2, deltas[1])
        result["baseline_window_ps"] = anchor_ps
        result["predicted_window_ps"] = anchor_ps - 36 * saved
        result["predicted_tok_s"] = tokens * 1e12 / result["predicted_window_ps"]
    if len(new) == expected and (candidate / "timing-audit.json").is_file():
        key = "interval_tok_s" if mode == "decode" else "prefill_tokens_per_second"
        result["measured_tok_s"] = json.loads((candidate / "timing-audit.json").read_bytes())[key]
        if mode == "decode" and result["baseline_complete"]:
            x, y = (json.loads((root / "execution.json").read_bytes()) for root in (base, candidate))
            if ([r[0] for r in x["retirements"]] != [r[0] for r in y["retirements"]] or
                    x["kv_cross_step_read_beats"] != y["kv_cross_step_read_beats"]):
                raise ValueError("retirement or KV coverage differs")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("decode", "prefill"))
    parser.add_argument("baseline", type=Path)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("--anchor-ps", type=float, default=0)
    args = parser.parse_args()
    print(json.dumps(analyze(args.mode, args.baseline, args.candidate, args.anchor_ps), indent=2))


if __name__ == "__main__":
    main()

