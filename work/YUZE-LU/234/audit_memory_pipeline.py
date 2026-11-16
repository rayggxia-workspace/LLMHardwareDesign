"""Check matched pipeline trials and compute gains from completed runs."""

import argparse
import json
from itertools import zip_longest
from pathlib import Path


def compare(before, after, mode):
    results = [json.loads((p / "execution.json").read_bytes()) for p in (before, after)]
    audits = [json.loads((p / "timing-audit.json").read_bytes()) for p in (before, after)]
    for key in ("pages", "positions", "sram_port_bits", "deployment_sha256"):
        if results[0].get(key) != results[1].get(key):
            raise ValueError(f"mismatched {key}")
    for key in ("reads", "writes", "callbacks"):
        if results[0]["ddr"][key] != results[1]["ddr"][key]:
            raise ValueError(f"mismatched DDR {key}")
    if mode == "decode":
        for key in ("kv_cross_step_read_beats", "kv_binding_sha256"):
            if results[0][key] != results[1][key]:
                raise ValueError(f"mismatched {key}")
        if [x[0] for x in results[0]["retirements"]] != [x[0] for x in results[1]["retirements"]]:
            raise ValueError("mismatched retired tokens")
    else:
        if audits[0]["kv_stores"] != audits[1]["kv_stores"]:
            raise ValueError("mismatched prefill KV stores")
    pages = 0
    with (before / "page-timing.jsonl").open() as a, (after / "page-timing.jsonl").open() as b:
        for left, right in zip_longest(a, b):
            if left is None or right is None:
                raise ValueError("mismatched trace lengths")
            left, right = json.loads(left), json.loads(right)
            for key in ("generation", "step", "page", "mother_instruction_cycles"):
                if left[key] != right[key]:
                    raise ValueError(f"mismatched page {key}")
            for key in ("reads", "writes", "callbacks"):
                if left["ddr"].get(key, 0) != right["ddr"].get(key, 0):
                    raise ValueError(f"mismatched page DDR {key}")
            if sorted((c["provider"], c["count"]) for c in left["calls"]) != sorted(
                    (c["provider"], c["count"]) for c in right["calls"]):
                raise ValueError("mismatched page CALLs")
            pages += 1
    if pages != results[0]["pages"]:
        raise ValueError("page count does not match execution")
    metric = "interval_tok_s" if mode == "decode" else "prefill_tokens_per_second"
    baseline, candidate = [a[metric] for a in audits]
    return dict(mode=mode, baseline_tok_s=baseline, candidate_tok_s=candidate,
                gain_percent=100*(candidate/baseline-1), timing_calibrated=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("decode", "prefill"))
    parser.add_argument("before", type=Path)
    parser.add_argument("after", type=Path)
    options = parser.parse_args()
    print(json.dumps(compare(options.before, options.after, options.mode), indent=2))
