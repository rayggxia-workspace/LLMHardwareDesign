"""Audit AV read reductions and projection timing against the sealed pipeline baseline."""

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
    sram_pipeline = results[1].get("attn_sram_pipeline", False)
    if sram_pipeline:
        if results[0].get("attn_sram_pipeline", False):
            raise ValueError("expected a baseline and an ATT1 SRAM pipeline candidate")
        for key in ("pipeline_memory", "rtl_weight_fetch", "av_value_fetch", "dma_scope"):
            if results[0][key] != results[1][key]:
                raise ValueError(f"mismatched {key}")
        for key in ("window", "response_slots"):
            if results[0]["attention_kv"][key] != results[1]["attention_kv"][key]:
                raise ValueError(f"mismatched KV {key}")
    if mode == "decode":
        for key in ("kv_cross_step_read_beats", "kv_binding_sha256"):
            if results[0][key] != results[1][key]:
                raise ValueError(f"mismatched {key}")
        if [x[0] for x in results[0]["retirements"]] != [x[0] for x in results[1]["retirements"]]:
            raise ValueError("mismatched retired tokens")
    else:
        if audits[0]["kv_stores"] != audits[1]["kv_stores"]:
            raise ValueError("mismatched prefill KV stores")
    pages = saved_reads = 0
    ratios = {"legacy": 1, "selected": 2, "paired": 4, "paired-ping-pong": 4}
    before_ratio, ratio = (ratios[r.get("av_value_fetch", "legacy")] for r in results)
    with (before / "page-timing.jsonl").open() as a, (after / "page-timing.jsonl").open() as b:
        for left, right in zip_longest(a, b):
            if left is None or right is None:
                raise ValueError("mismatched trace lengths")
            left, right = json.loads(left), json.loads(right)
            for key in ("generation", "step", "page", "mother_instruction_cycles"):
                if left[key] != right[key]:
                    raise ValueError(f"mismatched page {key}")
            if "av_read_requests" in right:
                legacy = right["av_legacy_read_requests"]
                av = right["av_read_requests"]
            elif mode == "decode" and ratio == 2:
                # The first selected-only run predates the per-page AV counters.
                calls = sum(c["count"] for c in right["calls"] if c["provider"][1] == 827610177)
                legacy = calls * (512 + right["step"]) * 32
                av = legacy // ratio
            else:
                raise ValueError("missing AV counters")
            before_av = left.get("av_read_requests", legacy) if before_ratio == 1 else left["av_read_requests"]
            if before_ratio * before_av != legacy or ratio * av != legacy:
                raise ValueError("incorrect AV request count")
            saved_reads += before_av - av
            for key in ("reads", "writes", "callbacks"):
                reduction = 0 if key == "writes" else before_av - av
                if left["ddr"].get(key, 0) - right["ddr"].get(key, 0) != reduction:
                    raise ValueError(f"mismatched page DDR {key}")
            if sorted((c["provider"], c["count"]) for c in left["calls"]) != sorted(
                    (c["provider"], c["count"]) for c in right["calls"]):
                raise ValueError("mismatched page CALLs")
            if sram_pipeline:
                for instance, counts in left["sram"].items():
                    for key in ("read_beats", "write_beats", "read_bytes", "write_bytes"):
                        if counts.get(key, 0) != right["sram"][instance].get(key, 0):
                            raise ValueError(f"mismatched {instance} SRAM {key}")
            pages += 1
    if pages != results[0]["pages"]:
        raise ValueError("page count does not match execution")
    for key in ("reads", "writes", "callbacks"):
        expected = 0 if key == "writes" else saved_reads
        if results[0]["ddr"][key] - results[1]["ddr"][key] != expected:
            raise ValueError(f"unexpected total DDR {key} delta")
    metric = "interval_tok_s" if mode == "decode" else "prefill_tokens_per_second"
    baseline, candidate = [a[metric] for a in audits]
    return dict(mode=mode, baseline_tok_s=baseline, candidate_tok_s=candidate,
                gain_percent=100*(candidate/baseline-1), av_ddr_bytes_saved=64*saved_reads,
                av_mode=results[1]["av_value_fetch"],
                rtl_weight_fetch=results[1].get("rtl_weight_fetch", False),
                attn_sram_pipeline=sram_pipeline, timing_calibrated=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("decode", "prefill"))
    parser.add_argument("before", type=Path)
    parser.add_argument("after", type=Path)
    options = parser.parse_args()
    print(json.dumps(compare(options.before, options.after, options.mode), indent=2))
