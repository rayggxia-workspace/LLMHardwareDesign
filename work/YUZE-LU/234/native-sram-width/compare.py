"""Compare matched two-step SRAM port-width replays after both complete."""

from argparse import ArgumentParser
from collections import Counter
import json
from pathlib import Path


def collect(directory):
    result = json.loads((directory / "execution.json").read_bytes())
    audit = json.loads((directory / "timing-audit.json").read_bytes())
    rows = [json.loads(line) for line in (directory / "page-timing.jsonl").read_text().splitlines()]
    if (len(rows) != 582 or audit["pages_per_step"] != [291, 291] or
            result["completed_layers_in_current_position"] != 36):
        raise ValueError("expected both complete decode steps")
    return result, audit, rows


def category(row):
    index = row["page"]
    if index == 0:
        return "embedding"
    if index == 290:
        return "vocabulary"
    if index == 289:
        return "final_rms"
    return ("input_rms", "qkv_rope_kv_write", "attention", "o_projection",
            "attention_residual_ffn_rms", "ffn", "down_store", "final_residual")[(index - 1) % 8]


def compare(narrow_dir, wide_dir):
    narrow, baseline, narrow_pages = collect(narrow_dir)
    wide, candidate, wide_pages = collect(wide_dir)
    if (narrow.get("sram_port_bits", 128), wide["sram_port_bits"]) != (128, 512):
        raise ValueError("expected a 128-bit to 512-bit comparison")
    for key in ("deployment_sha256", "kv_binding_sha256", "dma_scope", "kv_cross_step_read_beats",
                "attention_kv"):
        if narrow[key] != wide[key]:
            raise ValueError(f"changed workload or service policy: {key}")
    if [x[0] for x in narrow["retirements"]] != [x[0] for x in wide["retirements"]]:
        raise ValueError("retired token IDs differ")
    totals = [Counter(), Counter()]
    for a, b in zip(narrow_pages, wide_pages):
        for key in ("generation", "step", "page", "mother_instruction_cycles"):
            if a[key] != b[key]:
                raise ValueError(f"page {a['generation']} differs: {key}")
        for key in ("reads", "writes", "callbacks"):
            if a["ddr"].get(key, 0) != b["ddr"].get(key, 0):
                raise ValueError(f"page {a['generation']} differs in DDR {key}")
        if sorted((x["provider"], x["count"]) for x in a["calls"]) != sorted(
                (x["provider"], x["count"]) for x in b["calls"]):
            raise ValueError(f"page {a['generation']} differs in dispatched calls")
        if a["step"] == 2:
            for total, row in zip(totals, (a, b)):
                total[category(row)] += row["end_ps"] - row["start_ps"]
    intervals = [narrow["retirement_interval_ps"], wide["retirement_interval_ps"]]
    if [sum(total.values()) for total in totals] != intervals:
        raise ValueError("page times do not reconcile to token retirement intervals")
    return dict(scope=wide["scope"], port_bits=[128, 512],
                retirements=[narrow["retirements"], wide["retirements"]],
                interval_ms=[ps / 1e9 for ps in intervals],
                tok_s=[baseline["interval_tok_s"], candidate["interval_tok_s"]],
                throughput_gain_percent=100 * (intervals[0] / intervals[1] - 1),
                decode_stage_ms={name: [total[name] / 1e9 for total in totals] for name in totals[0]},
                ddr={key: wide["ddr"][key] for key in ("reads", "writes", "callbacks")},
                wide_sram=wide["sram"])


if __name__ == "__main__":
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("narrow", type=Path)
    parser.add_argument("wide", type=Path)
    args = parser.parse_args()
    print(json.dumps(compare(args.narrow, args.wide), indent=2))
