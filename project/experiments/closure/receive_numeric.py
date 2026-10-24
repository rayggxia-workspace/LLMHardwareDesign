"""Independent bounded Granite integer-router receiver for Issue72.

No producer imports. This closes only captured router input -> integer top8/
Q15 gates, not expert/down/merge or whole-model quantization.
"""
import argparse
from decimal import Decimal, localcontext, ROUND_HALF_EVEN
from fractions import Fraction
import math
from pathlib import Path
import shutil

import numpy as np

from audit_io import need, load_json, save_json, sha, descriptor, verify_manifest, check_source, replace_artifact_hash
from integer_oracle import round_rational, shift_rne


def read_arrays(path):
    with np.load(path, allow_pickle=False) as z:
        return {k: z[k] for k in z.files}


def exact_exponent(peak, bits):
    result = []
    for value in np.asarray(peak).ravel():
        v = float(value)
        need(math.isfinite(v) and v >= 0, "finite nonnegative compiler peak")
        if v == 0:
            result.append(0)
            continue
        n, d = v.as_integer_ratio()
        d *= (1 << (bits - 1)) - 1
        exponent = n.bit_length() - d.bit_length()
        larger = n > d << exponent if exponent >= 0 else n << -exponent > d
        exponent += int(larger)
        need(-100 <= exponent <= 100, "compiler scale exponent contract")
        result.append(exponent)
    return np.asarray(result, np.int16).reshape(np.asarray(peak).shape)


def encode(source, exponents, bits):
    x = np.asarray(source, np.float64)
    rounded = np.rint(np.ldexp(x, -np.asarray(exponents, np.int32)))
    bound = (1 << (bits - 1)) - 1
    clipped = (rounded < -bound) | (rounded > bound)
    return np.minimum(bound, np.maximum(-bound, rounded)).astype(np.int8 if bits == 8 else np.int16), clipped


def integer_gate(logits, unit, selected, lut):
    codes, indices, clips = [], [], 0
    for values, exponent, ids in zip(logits, unit, selected):
        maximum = int(values[int(ids[0])])
        row_indices = []
        for expert in ids:
            delta = int(values[int(expert)]) - maximum
            grid = shift_rne(delta * 1549082005, 23 - int(exponent))
            need(grid <= 0, "selected expert order")
            clips += int(grid < -2048)
            row_indices.append(min(2048, -grid))
        terms = [int(lut[i]) for i in row_indices]
        denominator = sum(terms)
        row = [round_rational(value << 15, denominator) for value in terms]
        row[0] += 32768 - sum(row)
        need(min(row) >= 0 and max(row) <= 32768 and sum(row) == 32768,
             "Q15 gate conservation")
        codes.append(row)
        indices.append(row_indices)
    return np.asarray(codes, np.uint16), np.asarray(indices, np.int16), clips


def certify(logits, selected, aq, wq, weight_exponents, clipped):
    lower = int(min(weight_exponents))
    bound = np.empty(logits.shape, np.int64)
    # Reuse exact sums over complete fixed rows. Repeating these inside every
    # token/expert pair would add billions of redundant Python additions.
    weight_sums = [sum(abs(int(v)) for v in row) for row in wq]
    for row in range(len(logits)):
        asum = sum(abs(int(v)) for v in aq[row])
        for col in range(len(wq)):
            wsum = weight_sums[col]
            error = (2 * asum + 2 * wsum + aq.shape[1] + 3) // 4
            error *= 1 << (int(weight_exponents[col]) - lower)
            need(error < 1 << 63, "certification bound S64")
            bound[row, col] = error
    flags = []
    for row, ids in enumerate(selected):
        chosen = set(map(int, ids))
        lo = min(int(logits[row, i]) - int(bound[row, i]) for i in chosen)
        hi = max(int(logits[row, i]) + int(bound[row, i]) for i in range(40) if i not in chosen)
        flags.append(not clipped[row].any() and lo > hi)
    return np.asarray(flags, np.bool_), bound


def metric(a, ref):
    x, y = np.asarray(a, np.float64), np.asarray(ref, np.float64)
    need(x.shape == y.shape and np.isfinite(x).all() and np.isfinite(y).all(), "finite error tensors")
    delta = x - y
    return {"relative_l2": float(np.sqrt(np.sum(delta * delta)) / max(float(np.sqrt(np.sum(y * y))), 1e-30)),
            "max_abs": float(np.max(np.abs(delta), initial=0))}


def match_metric(actual, expected):
    for name, value in expected.items():
        need(math.isclose(float(actual[name]), value, rel_tol=3e-11, abs_tol=1e-13),
             "independent reported error " + name)


def same(a, b, label):
    need(np.asarray(a).shape == np.asarray(b).shape and np.asarray(a).dtype == np.asarray(b).dtype
         and np.array_equal(a, b), label)


def verify(result, reference, producer_source):
    result, reference = Path(result), Path(reference)
    m, checked = verify_manifest(result, kind="granite_numeric72", statuses=("EXECUTED_INTEGER_ROUTER_DIAGNOSTIC",))
    source_sha = check_source(m, producer_source, "granite_numeric_sha256")
    rm, rc = verify_manifest(reference, kind="granite_reference72", statuses=("EXECUTED_REFERENCE",))
    need(m["reference_manifest_sha256"] == sha(reference / "manifest.json")
         and m["reference_self_consistency"] == rm["reference_self_consistency"]
         and m["reference_precision"] == rm["precision_variant"]
         and m["original_issue70_status"] == "FAIL" and m["performance_eligible"] is False,
         "typed reference provenance and qualification")
    z, src = read_arrays(result / "numeric.npz"), read_arrays(reference / "trace.npz")
    report = load_json(result / "report.json")
    need(report["original_issue70_status"] == "FAIL" and report["reference_self_consistency"] == rm["reference_self_consistency"],
         "failure retained in router report")
    need(len(report["records"]) == 768 and len(report["selective_wide"]) == 192
         and report["records_expected"] == 768, "all 768 candidates and 192 selective records")
    # A Decimal compiler oracle independently checks every irrational exp2 LUT
    # entry rather than invoking producer's NumPy exponential implementation.
    with localcontext() as ctx:
        ctx.prec = 70
        lut = np.asarray([int(((Decimal(2) ** (-Decimal(i) / 128)) * (1 << 24)).to_integral_value(rounding=ROUND_HALF_EVEN))
                          for i in range(2049)], np.uint32)
    same(lut, z["lut.exp2_q24"], "independent Decimal LUT compiler")
    records = {(r["case"], r["profile"], r["layer"], r["mode"], r["bits"]): r for r in report["records"]}
    selective_records = {(r["case"], r["profile"], r["layer"]): r for r in report["selective_wide"]}
    need(len(records) == 768 and len(selective_records) == 192, "unique result keys")
    checked_keys = {"lut.exp2_q24"}
    dots = lowered_dots = certificates = fallback_rows = 0
    for layer in range(32):
        w = src[f"router_weight.{layer}"].astype(np.float64)
        cal = src[f"calibration.full.{layer}.router_input"].astype(np.float64)
        weights = {}
        for bits in (8, 16):
            exp = exact_exponent(np.max(np.abs(w), axis=1), bits)
            code, clip = encode(w, exp[:, None], bits)
            need(not clip.any(), "weight encoding unclipped")
            for suffix, value in (("weight_code", code), ("weight_exp", exp)):
                key = f"layer{layer}.b{bits}.{suffix}"
                same(value, z[key], "compiler weight " + key)
                checked_keys.add(key)
            weights[bits] = code, exp
        for case in ("calibration", "evaluation"):
            for profile in ("full", "cached64", "chunk16"):
                prefix = f"{case}.{profile}.{layer}."
                x = src[prefix + "router_input"].astype(np.float64)
                f64 = x @ w.T
                stored_f64 = z[prefix + "same_input_fp64_logits"]
                allowed = (2 * x.shape[1] + 2) * np.finfo(np.float64).eps * (np.abs(x) @ np.abs(w).T)
                need(np.all(np.abs(f64 - stored_f64) <= allowed), "same-input FP64 diagnostic dot bound")
                fids = np.asarray([sorted(range(40), key=lambda j: (-float(row[j]), j))[:8] for row in stored_f64], np.int16)
                selected = np.take_along_axis(stored_f64, fids, 1)
                exp_values = np.exp(selected - selected.max(axis=1, keepdims=True))
                fgate = exp_values / exp_values.sum(axis=1, keepdims=True)
                same(fids, z[prefix + "same_input_fp64_ids"], "diagnostic exact-score top8")
                need(np.all(np.abs(fgate - z[prefix + "same_input_fp64_gate"]) <= 8 * np.finfo(np.float64).eps), "diagnostic gate")
                checked_keys.update(prefix + "same_input_fp64_" + k for k in ("logits", "ids", "gate"))
                candidates = {}
                for mode in ("calibration_static", "dynamic_row"):
                    for bits in (8, 16):
                        wp, we = weights[bits]
                        peak = np.full(len(x), np.max(np.abs(cal))) if mode == "calibration_static" else np.max(np.abs(x), axis=1)
                        ae = exact_exponent(peak, bits)
                        aq, clipping = encode(x, ae[:, None], bits)
                        dot = aq.astype(np.int64) @ wp.astype(np.int64).T
                        worst = 1536 * ((1 << (bits - 1)) - 1) ** 2
                        need(int(np.max(np.abs(dot))) <= worst < 1 << 63, "complete-K worst bound")
                        common = np.empty(dot.shape, np.int64)
                        for col in range(40):
                            scale = 1 << (int(we[col]) - int(min(we)))
                            need(int(np.max(np.abs(dot[:, col]))) * scale < 1 << 63, "common logit width")
                            common[:, col] = dot[:, col] * scale
                        ce = (ae + int(min(we))).astype(np.int16)
                        ids = np.asarray([sorted(range(40), key=lambda j: (-int(row[j]), j))[:8] for row in common], np.int16)
                        gate, indices, clips = integer_gate(common, ce, ids, lut)
                        cert, bounds = certify(common, ids, aq, wp, we, clipping)
                        values = {"input_code": aq, "input_exp": ae, "dot": dot, "common_logits": common,
                                  "common_exp": ce, "ids": ids, "gate_q15": gate, "lut_index": indices,
                                  "input_saturated": clipping.any(axis=1), "certified_top8": cert, "error_bound_codes": bounds}
                        out_prefix = prefix + mode + f".b{bits}."
                        for suffix, value in values.items():
                            key = out_prefix + suffix
                            same(value, z[key], "integer router " + key)
                            checked_keys.add(key)
                        row = records[(case, profile, layer, mode, bits)]
                        dots += dot.size
                        certificates += int(cert.sum())
                        changed = np.any(np.sort(ids, axis=1) != np.sort(fids, axis=1), axis=1)
                        need(not np.any(cert & changed), "strict certified ranking versus same-input reference")
                        for key, expected in {"same_input_fp64_set_changed_tokens": int(changed.sum()),
                                              "source_reference_set_changed_tokens": int(np.any(np.sort(ids, axis=1) != np.sort(src[prefix + 'ids'], axis=1), axis=1).sum()),
                                              "same_input_fp64_order_changed_tokens": int(np.any(ids != fids, axis=1).sum()),
                                              "input_saturated_elements": int(clipping.sum()),
                                              "certified_top8_tokens": int(cert.sum()), "lut_domain_clips": clips,
                                              "full_K_dot_absolute_worst_bound": worst,
                                              "full_K_dot_signed_bits_worst_bound": worst.bit_length() + 1,
                                              "S8_MACs_per_row": 1536 * 40 * (1 if bits == 8 else 9),
                                              "integer_weight_bytes": wp.nbytes, "weight_exp_int16_bytes": we.nbytes,
                                              "input_payload_bytes_per_row": 1536 * (bits // 8), "LUT_uint32_payload_bytes": lut.nbytes}.items():
                            need(row[key] == expected, "reported router inventory " + key)
                        decoded = np.ldexp(common.astype(np.float64), ce[:, None])
                        match_metric(row["logits_error"], metric(decoded, stored_f64))
                        exact_selected = np.take_along_axis(stored_f64, ids, 1)
                        e = np.exp(exact_selected - exact_selected.max(axis=1, keepdims=True))
                        match_metric(row["gate_vs_same_selected_fp64"], metric(gate.astype(np.float64) / 32768, e / e.sum(axis=1, keepdims=True)))
                        if bits == 16:
                            sorted_scores = np.sort(stored_f64, axis=1)
                            rows = sorted(set((0, len(x) - 1, int(np.argmin(sorted_scores[:, -8] - sorted_scores[:, -9])))))
                            same(np.asarray(rows, np.int16), z[out_prefix + "lowering_rows"], "predeclared complete lowering rows")
                            av, wv = aq[rows].astype(np.int64), wp.astype(np.int64)
                            a_sign, w_sign = np.where(av < 0, -1, 1), np.where(wv < 0, -1, 1)
                            parts, rebuilt = [], np.zeros((len(rows), 40), np.int64)
                            for i in range(3):
                                da = (((np.abs(av) >> (7 * i)) & 127) * a_sign).astype(np.int64)
                                for j in range(3):
                                    dw = (((np.abs(wv) >> (7 * j)) & 127) * w_sign).astype(np.int64)
                                    partial = da @ dw.T
                                    need(np.max(np.abs(partial)) <= 1536 * 127 * 127 < 1 << 31, "lowering INT32 all-prefix bound")
                                    parts.append(partial.astype(np.int32))
                                    rebuilt += partial * (1 << (7 * (i + j)))
                            same(np.stack(parts), z[out_prefix + "lowering_partials"], "nine actual full-K S8 partials")
                            need(np.array_equal(rebuilt, dot[rows]) and row["lowering_witness_rows"] == rows,
                                 "wide exact reconstruction")
                            checked_keys.update(out_prefix + k for k in ("lowering_rows", "lowering_partials"))
                            lowered_dots += 9 * len(rows) * 40
                        candidates[(mode, bits)] = (ids, gate, cert)
                low, high = candidates[("dynamic_row", 8)], candidates[("dynamic_row", 16)]
                fallback = ~low[2]
                selective_ids = np.where(fallback[:, None], high[0], low[0])
                selective_gate = np.where(fallback[:, None], high[1], low[1])
                for suffix, value in (("fallback_w16", fallback), ("ids", selective_ids), ("gate_q15", selective_gate)):
                    same(value, z[prefix + "selective." + suffix], "causal selective route " + suffix)
                    checked_keys.add(prefix + "selective." + suffix)
                record = selective_records[(case, profile, layer)]
                expected = {"fallback_rows": int(fallback.sum()), "tokens": len(x),
                            "remaining_uncertified_rows": int(np.count_nonzero(fallback & ~high[2])),
                            "same_input_fp64_set_changed_tokens": int(np.any(np.sort(selective_ids, axis=1) != np.sort(fids, axis=1), axis=1).sum()),
                            "charged_S8_MACs": len(x) * 1536 * 40 + int(fallback.sum()) * 9 * 1536 * 40}
                need(all(record[k] == v for k, v in expected.items()), "selective fallback/cost inventory")
                fallback_rows += int(fallback.sum())
        print("verified layer", layer, flush=True)
    need(set(z) == checked_keys, "exact complete numeric artifact key index")
    return {"status": "PASS", "source_sha256": source_sha, "reference_precision": rm["precision_variant"],
            "reference_self_consistency": rm["reference_self_consistency"], "original_issue70_status": "FAIL",
            "records_checked": 768, "selective_records_checked": 192, "complete_dots_checked": dots,
            "actual_fullK_S8_lowering_partials_checked": lowered_dots, "certified_rows": certificates,
            "selective_fallback_rows": fallback_rows, "artifacts": checked, "reference_artifacts": rc,
            "performance_eligible": False,
            "limits": ["Captured-router-input cut only; no expert/down/merge/LLM integer closure or application quality acceptance",
                       "All router candidates mathematically replayed; W16 physical execution only selected full-K S8 witnesses, other dots software INT64 oracle",
                       "Scale and Decimal LUT compiler bridges explicit; target wide arithmetic/LUT/divider/timing/RTL/PPA remain unqualified"]}


def main():
    p = argparse.ArgumentParser(__doc__)
    for key in ("result", "reference", "producer-source", "binding", "out"):
        p.add_argument("--" + key, type=Path, required=True)
    p.add_argument("--skip-negatives", action="store_true")
    args = p.parse_args()
    need(not args.out.exists(), "refuse output overwrite")
    binding = load_json(args.binding)
    for name in ("receive_numeric", "audit_io", "integer_oracle"):
        need(binding.get(name + "_sha256") == sha(Path(__file__).with_name(name + ".py")), "receiver dependency " + name)
    args.out.mkdir(parents=True)
    receipt = verify(args.result, args.reference, args.producer_source)
    receipt["receiver"] = binding
    receipt["semantic_negatives"] = [] if args.skip_negatives else negatives(
        args.result, args.reference, args.producer_source, args.out)
    if args.skip_negatives:
        receipt["status"] = "PARTIAL_NO_NEGATIVES"
    save_json(args.out / "receipt.json", receipt)
    print(receipt["status"], receipt["records_checked"], flush=True)


def negatives(result, reference, producer_source, out):
    receipts = []
    for name, key in (("code", "calibration.full.0.calibration_static.b8.input_code"),
                      ("lut", "lut.exp2_q24"),
                      ("gate", "calibration.full.0.calibration_static.b8.gate_q15"),
                      ("fallback", "calibration.full.0.selective.fallback_w16")):
        case = Path(out) / ("negative-" + name)
        shutil.copytree(result, case)
        values = read_arrays(case / "numeric.npz")
        values[key].flat[0] ^= True if values[key].dtype.kind == "b" else 1
        np.savez_compressed(case / "numeric.npz", **values)
        replace_artifact_hash(case, "numeric.npz")
        verify_manifest(case, kind="granite_numeric72", statuses=("EXECUTED_INTEGER_ROUTER_DIAGNOSTIC",))
        try:
            verify(case, reference, producer_source)
        except (ValueError, AssertionError) as error:
            receipts.append({"case": name, "artifact_hash_rewritten": True,
                             "artifact_hash_layer_passed": True, "semantic_rejected": True,
                             "reason": str(error), "mutated_manifest": descriptor(case / "manifest.json")})
        else:
            raise ValueError("semantic negative accepted: " + name)
    return receipts


if __name__ == "__main__":
    main()
