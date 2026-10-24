"""Independent frozen-input Falcon grouped-out-projection receipt."""
import argparse
import math
from pathlib import Path
import shutil

import numpy as np

from audit_io import need, load_json, save_json, sha, descriptor, verify_manifest, replace_artifact_hash
from integer_oracle import shift_rne
from receive_falcon import Replay, i32, array_hash, load_arrays, reference_metric


def wire_bytes(payload):
    full, tail = divmod(int(payload), 1984)
    return full * 2016 + (32 + ((tail + 15) // 16) * 16 if tail else 0)


def equal(a, b, name):
    need(a.shape == b.shape and a.dtype == b.dtype and np.array_equal(a, b), "grouped integer stage " + name)


def reconstruct_i128(high, low):
    h, l = int(high), int(low)
    need(-(1 << 63) <= h < 1 << 63 and 0 <= l < 1 << 64, "physical I128 hi/lo words")
    return h * (1 << 64) + l


def verify(result, baseline, baseline_receipt, compiled, producer_source):
    result, baseline, compiled = Path(result), Path(baseline), Path(compiled)
    m, artifacts = verify_manifest(result, statuses=("EXECUTED",))
    bm, ba = verify_manifest(baseline, statuses=("EXECUTED",))
    cm, ca = verify_manifest(compiled, statuses=("EXECUTED",))
    need(m["schema"] == "falcon-outproj-granularity-v1"
         and m["source"]["falcon_outproj_sha256"] == sha(producer_source), "outproj frozen source")
    receipt = load_json(baseline_receipt)
    need(receipt["status"] == "PASS" and receipt["mode"] == "full" and receipt["state_bits"] == 32
         and receipt["policy"] == "guard_rescale" and receipt["committed_tokens"] == 72
         and receipt["artifacts"] == ba and receipt["compiled_artifacts"] == ca
         and receipt["producer_manifest"] == descriptor(baseline / "manifest.json"), "independent complete baseline binding")
    report, alignment = load_json(result / "report.json"), load_json(result / "alignment.json")
    old, z, const = load_arrays(baseline / "runtime.npz"), load_arrays(result / "outproj.npz"), load_arrays(compiled / "constants.npz")
    spec = load_json(compiled / "spec.json")
    need(report["baseline_manifest_sha256"] == sha(baseline / "manifest.json")
         and report["compiled_manifest_sha256"] == sha(compiled / "manifest.json"), "fixed baseline and compiler")
    group = report["group_k"]
    need(group in (0, 512, 256), "predeclared group size")
    x, w = old["gated_norm_q12"], const["out_weight_w8"]
    t, k = x.shape
    o = w.shape[0]
    need((t, k, o) == (72, 4096, 2560), "complete frozen projection shape")
    gk = group or k
    groups = k // gk
    need(report["groups"] == groups, "actual group count")
    for key, value in {"frozen_input_array_sha256": x, "frozen_weight_array_sha256": w,
                       "fixed_w_scale_array_sha256": const["out_scale_q31"],
                       "fixed_w_exp_array_sha256": const["out_scale_exp"]}.items():
        need(report[key] == array_hash(value), "fixed untouched numeric input " + key)
    equal(x, z["input_q12"], "frozen gatednorm input")
    eng = Replay()
    a8, delta = np.empty(x.shape, np.int8), np.empty((t, groups), np.int16)
    parts = np.empty((t, groups, o), np.int32)
    for row in range(t):
        for g in range(groups):
            source = x[row, g * gk:(g + 1) * gk]
            d = 0
            while max(abs(int(v)) for v in eng.shift(source, d)) > 127:
                d += 1
            delta[row, g] = d
            a8[row, g * gk:(g + 1) * gk] = eng.shift(source, d).astype(np.int8)
    equal(a8, z["a8"], "minimal dynamic A8")
    equal(delta, z["a8_delta"], "actual I16 per-group exponent")
    need(gk * 127 * 127 < 1 << 31, "INT32 all-prefix partial bound")
    for g in range(groups):
        parts[:, g] = i32(a8[:, g * gk:(g + 1) * gk].astype(np.int64) @ w[:, g * gk:(g + 1) * gk].astype(np.int64).T)
    equal(parts, z["partial_acc32"], "all complete-group INT32 dots")
    common = delta.min(axis=1).astype(np.int16)
    equal(common, z["common_delta"], "finest complete-K unit")
    need(alignment["one_final_rne_after_complete_k"] is True and len(alignment["rows"]) == t * groups,
         "one final requantization after complete K")
    total = np.zeros((t, o), np.int64)
    for row in range(t):
        for g in range(groups):
            left = int(delta[row, g]) - int(common[row])
            aligned = eng.shift(parts[row, g], -left) if left else parts[row, g].astype(np.int64)
            total[row] = aligned.copy() if g == 0 else eng.add(total[row], aligned)
            actual = alignment["rows"][row * groups + g]
            expected = {"row": row, "group": g, "delta": int(delta[row, g]), "common_delta": int(common[row]),
                        "leftshift": left, "partial_sha256": array_hash(parts[row, g]),
                        "aligned_sha256": array_hash(aligned), "prefix_sum_sha256": array_hash(total[row]),
                        "aligned_max_abs": max(abs(int(v)) for v in aligned),
                        "prefix_max_abs": max(abs(int(v)) for v in total[row])}
            need(actual == expected, "complete ordered alignment witness")
    equal(total, z["aligned_sum_i64"], "full K aligned I64 sum")
    high, low, out = np.empty((t, o), np.int64), np.empty((t, o), np.uint64), np.empty((t, o), np.int64)
    largest = 0
    for row in range(t):
        for col in range(o):
            product = int(total[row, col]) * int(const["out_scale_q31"][col])
            need(-(1 << 127) <= product < 1 << 127, "I128 checked product")
            if groups == 1:
                need(-(1 << 63) < product < 1 << 63, "whole-row preserves original I64 contract")
            high[row, col], low[row, col] = product >> 64, product & ((1 << 64) - 1)
            need(reconstruct_i128(high[row, col], low[row, col]) == product, "signed hi/unsigned lo reconstruction")
            out[row, col] = shift_rne(product, 31 - int(const["out_scale_exp"][col]) - int(common[row]))
            largest = max(largest, abs(product))
    expected = {"input_q12": x, "a8": a8, "a8_delta": delta, "common_delta": common,
                "partial_acc32": parts, "aligned_sum_i64": total, "rq_product_hi_i64": high,
                "rq_product_lo_u64": low, "out_before_bias_q12": i32(out),
                "residual_q12": old["input_q12"], "external_attention_q12": old["external_attention_q12"]}
    y = i32(eng.add(expected["out_before_bias_q12"], const["out_bias_q12"]))
    mamba = i32(eng.scaled(y, const["ssm_out_multiplier_q20"], 20))
    attention = i32(eng.scaled(old["external_attention_q12"], const["attention_out_multiplier_q20"], 20))
    joined = i32(eng.add(eng.add(old["input_q12"], mamba), attention))
    expected.update(out_linear_q12=y, mamba_scaled_q12=mamba, attention_scaled_q12=attention,
                    join_q12=joined, next_norm_q12=eng.norm(joined, const["next_gamma_q20"], spec["epsilon_q24"]))
    need(set(expected) == set(z), "complete grouped integer chain stage set")
    for name, value in expected.items():
        equal(value, z[name], name)
    compare = {name: bool(np.array_equal(expected[name], old[name])) for name in
               ("out_linear_q12", "mamba_scaled_q12", "attention_scaled_q12", "join_q12", "next_norm_q12")}
    if groups == 1:
        compare.update(a8=bool(np.array_equal(a8, old["out_a8"])),
                       a8_delta=bool(np.array_equal(delta[:, 0], old["out_a8_delta"])),
                       partial_acc32=bool(np.array_equal(parts[:, 0], old["out_acc32"])))
        need(all(compare.values()), "whole-row baseline exact control")
    need(report["whole_row_comparison"] == compare, "baseline comparison records")
    costs = report["costs"]
    for name, value in {"partial_dot_payload_bytes": t * groups * o * 4,
                        "partial_dot_wire_bytes": t * groups * wire_bytes(o * 4),
                        "a8_delta_payload_bytes": t * groups * 2, "a8_delta_wire_bytes": t * wire_bytes(groups * 2),
                        "fixed_weight_w8_payload_bytes": w.nbytes, "fixed_output_scale_payload_bytes": o * 6,
                        "common_delta_witness_bytes": common.nbytes}.items():
        need(costs[name] == value, "actual grouped protocol inventory " + name)
    need(costs["common_delta_transmission_required"] is False, "derived common unit is not gratuitous transmitted metadata")
    width = report["widths"]
    need(width["largest_aligned_sum_magnitude_bits"] == max(abs(int(v)) for v in total.ravel()).bit_length()
         and width["largest_product_magnitude_bits"] == largest.bit_length()
         and width["observed_rq_products_fit_i64"] is (largest <= (1 << 63) - 1)
         and width["declared_alignment_bits"] == (32 if groups == 1 else 64)
         and width["declared_rq_product_bits"] == (64 if groups == 1 else 128)
         and width["partial_worst_int32_absolute_bound"] == gk * 127 * 127, "actual and declared widths")
    # Diagnostic float errors are only read after the entire integer result.
    ref = load_arrays(compiled / "reference.npz")
    for phase, selection in ((None, slice(None)), ("prefill64", slice(0, 64)), ("decode8", slice(64, 72))):
        for key, suffix in (("out_linear_q12", "mamba"), ("join_q12", "pre_ff_input"), ("next_norm_q12", "next_norm_reference")):
            actual = report["reference_errors"][key] if phase is None else report["phase_errors"][phase][key]
            metrics = {"vs_native_reference": reference_metric(expected[key][selection].astype(np.float64) / 4096,
                                                               ref["evaluation." + suffix][selection]),
                       "vs_frozen_integer_baseline": reference_metric(expected[key][selection], old[key][selection])}
            for target, values in metrics.items():
                need(all(math.isclose(actual[target][n], v, rel_tol=3e-11, abs_tol=1e-13) for n, v in values.items()),
                     "independent grouped post-run errors")
    return {"status": "PASS", "group_k": group, "groups": groups, "integer_stages_checked": len(expected),
            "full_group_INT32_outputs_checked": parts.size, "I128_products_checked": high.size,
            "baseline_receipt": descriptor(baseline_receipt), "artifacts": artifacts,
            "limits": ["One fixed already integer gatednorm trajectory; R/norm/weights not refitted",
                       "Exact software full-K alignment and I128 reference; no native integer kernel, model quality, placement benefit or RTL/PPA acceptance",
                       "Concrete partial streams/scale metadata counted, not an unavoidable end-to-end lower bound"]}


def negatives(result, baseline, baseline_receipt, compiled, producer_source, out):
    result = Path(result)
    records = []
    for name, key in (("A8_code", "a8"), ("I128_product", "rq_product_lo_u64"), ("alignment_unit", None)):
        folder = Path(out) / ("negative-" + name)
        shutil.copytree(result, folder)
        if key:
            arrays = load_arrays(folder / "outproj.npz")
            arrays[key].flat[0] ^= 1
            np.savez_compressed(folder / "outproj.npz", **arrays)
            replace_artifact_hash(folder, "outproj.npz")
        else:
            record = load_json(folder / "alignment.json")
            record["rows"][0]["common_delta"] += 1
            save_json(folder / "alignment.json", record)
            replace_artifact_hash(folder, "alignment.json")
        verify_manifest(folder, statuses=("EXECUTED",))
        try:
            verify(folder, baseline, baseline_receipt, compiled, producer_source)
        except (ValueError, AssertionError) as error:
            records.append({"case": name, "hash_layer_passed_after_SHA_rewrite": True,
                            "semantic_rejected": True, "reason": str(error),
                            "mutated_manifest": descriptor(folder / "manifest.json")})
        else:
            raise ValueError("grouped negative accepted " + name)
    return records


def main():
    ap = argparse.ArgumentParser(__doc__)
    for name in ("result", "baseline", "baseline-receipt", "compiled", "producer-source", "binding", "out"):
        ap.add_argument("--" + name, type=Path, required=True)
    ap.add_argument("--skip-negatives", action="store_true")
    args = ap.parse_args()
    need(not args.out.exists(), "refuse output overwrite")
    binding = load_json(args.binding)
    for name in ("receive_outproj", "receive_falcon", "audit_io", "integer_oracle"):
        need(binding.get(name + "_sha256") == sha(Path(__file__).with_name(name + ".py")), "receiver source " + name)
    args.out.mkdir(parents=True)
    receipt = verify(args.result, args.baseline, args.baseline_receipt, args.compiled, args.producer_source)
    receipt["receiver"] = binding
    receipt["semantic_negatives"] = [] if args.skip_negatives else negatives(
        args.result, args.baseline, args.baseline_receipt, args.compiled, args.producer_source, args.out)
    if args.skip_negatives:
        receipt["status"] = "PARTIAL_NO_NEGATIVES"
    save_json(args.out / "receipt.json", receipt)
    print(receipt["status"], receipt["groups"], flush=True)


if __name__ == "__main__":
    main()
