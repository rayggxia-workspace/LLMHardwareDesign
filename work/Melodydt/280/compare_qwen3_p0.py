"""Validate P0-only Qwen3 and compare its DDR windows with the verified three-P run."""
import argparse
from collections import Counter
import json
from pathlib import Path
from struct import unpack_from

from audit_short import audit
from compare_fp32_layers import compare
from ddr_window_energy import evaluate, load


STAGES = ("prefill-w4-tile128-pr272-combined", "decode-live-w4-tile128-pr272-combined")


def scratch_routes(directory):
    stores, down = Counter(), Counter()
    for image in (directory / "assets").glob("*-descriptors.bin"):
        data = image.read_bytes()
        if len(data) % 128:
            raise ValueError(f"unaligned descriptors in {image}")
        for offset in range(0, len(data), 128):
            descriptor = data[offset:offset+128]
            schema, _, op = unpack_from("<IHH", descriptor)
            if (schema, op) == (9, 1):
                address, _, words = unpack_from("<QHH", descriptor, 16)
                if address >= 15 << 30:
                    stores[address, words * 16] += 1
            if schema == 0x02505001 and descriptor[16] == 4:
                backing, = unpack_from("<Q", descriptor, 24)
                weight, = unpack_from("<Q", descriptor, 48)
                first, = unpack_from("<I", descriptor, 68)
                inner, = unpack_from("<H", descriptor, 76)
                down[backing, weight, first, inner] += 1
    if not stores or not down:
        raise ValueError("missing DDR-backed FFN store or route-4 descriptor")
    return stores, down


def input_images(plan):
    return Counter((Path(i["path"]).name, i["bytes"], i["sha256"])
                   for i in plan["images"] if not Path(i["path"]).name.startswith("pos"))


def records(result, active):
    lanes = result["ffn_by_target"]
    if set(lanes) != {"0", "1", "2"}:
        raise ValueError("three-target runtime was not preserved")
    total = 0
    for site, values in lanes.items():
        record_count = values.get("weight_records_consumed", 0)
        issued, returns = (values.get(k, 0) for k in ("weight_read_issues", "weight_read_returns"))
        if issued != returns or (site in active) != bool(record_count and issued):
            raise ValueError(f"unexpected lane activity or missing completion for site {site}")
        if site not in active and (record_count or issued):
            raise ValueError(f"idle FFN site {site} consumed weights")
        total += record_count
    return total


def comparison(baseline, candidate, reference, fp32):
    a, b = (load(d / "result.json") for d in (baseline, candidate))
    ap, bp = (load(d / "assets/plan.json") for d in (baseline, candidate))
    if not ap["three_p"] or not bp["three_p"] or ap.get("ffn_p0_only") or not bp.get("ffn_p0_only"):
        raise ValueError("unexpected FFN configuration for A/B")
    for k in ("history", "first_decode_input", "layers", "state", "scratch", "local"):
        if ap[k] != bp[k]:
            raise ValueError(f"frozen geometry or input changed: {k}")
    for k in ("history_payload", "history_source_sha256", "cross_step_reads", "weight_window",
              "pr272_profile", "tiled_attention128", "residual_fraction_bits"):
        if a.get(k) != b.get(k):
            raise ValueError(f"configuration or state changed: {k}")
    if input_images(ap) != input_images(bp) or scratch_routes(baseline) != scratch_routes(candidate):
        raise ValueError("packed input or DDR scratch contract changed")
    if records(a, {"0", "1", "2"}) != records(b, {"0"}):
        raise ValueError("A/B used different FFN record totals")
    if load(baseline / "layer-trace.json") != load(candidate / "layer-trace.json"):
        raise ValueError("A/B changed layer outputs")
    keys = ("input", "selected", "vocab", "logits_sha256")
    if [[x[k] for k in keys] for x in a["retirements"]] != [[x[k] for k in keys] for x in b["retirements"]]:
        raise ValueError("A/B changed vocabulary output")
    verdict = audit(candidate, b["layers"], bp["vocab"], b["mode"], reference)
    trace = compare(reference, fp32, candidate)
    if (b["residual_saturations"] or len(trace["rows"]) != b["layers"] * 2 or
            (b["mode"] == "decode" and not all(x.get("top1_equal") for x in verdict["numeric"]))):
        raise ValueError("P0-only numerical audit failed")
    left, right = (evaluate(d)["windows"] for d in (baseline, candidate))
    report = {}
    for name in left:
        report[name] = {
            "three_p": left[name], "p0_only": right[name],
            "three_p_speed_gain_pct": 100 * (left[name]["tok_s"] / right[name]["tok_s"] - 1),
            "three_p_ddr_energy_change_pct":
                100 * (left[name]["device_mj_per_token"] / right[name]["device_mj_per_token"] - 1),
        }
    return {"windows": report, "p0_audit": verdict}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("baseline", "candidate", "reference", "fp32"):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    print(json.dumps({stage: comparison(args.baseline / stage, args.candidate / stage,
                                       args.reference, args.fp32) for stage in STAGES}, indent=2))
