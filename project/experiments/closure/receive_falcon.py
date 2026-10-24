"""Independent Issue72 Falcon integer-chain replay (no producer imports).

All numerical runtime replay uses integer arrays or Python integers.  Float
reference errors are evaluated only after the independent integer result.
"""
import argparse
import ast
from collections import Counter
import hashlib
import json
from pathlib import Path
import shutil

import numpy as np

from audit_io import (need, load_json, save_json, sha, descriptor,
                      verify_manifest, replace_artifact_hash)
from integer_oracle import divided_rne, isqrt_bits, round_rational

I64 = (1 << 63) - 1


def load_arrays(path):
    with np.load(path, allow_pickle=False) as source:
        return {k: source[k] for k in source.files}


def array_hash(a):
    x = np.ascontiguousarray(a)
    prefix = str(x.dtype).encode() + json.dumps(list(x.shape), separators=(",", ":")).encode()
    return hashlib.sha256(prefix + x.tobytes()).hexdigest()


def magnitude(a):
    x = np.asarray(a)
    need(x.dtype.kind in "iu", "integer-only replay")
    lo, hi = int(x.min(initial=0)), int(x.max(initial=0))
    need(-(1 << 63) < lo and hi <= I64, "bounded signed I64 replay input")
    return max(-lo, hi)


def i32(a):
    x = np.asarray(a)
    need(x.dtype.kind in "iu" and int(x.min(initial=0)) >= -(1 << 31)
         and int(x.max(initial=0)) < 1 << 31, "I32 stage bound")
    return x.astype(np.int32)


class Replay:
    def __init__(self):
        self.ops = Counter()

    def multiply(self, a, b, left_bits=32, right_bits=32):
        x, y = np.asarray(a), np.asarray(b)
        need(magnitude(x) * magnitude(y) <= I64, "I64 multiply bound")
        need(int(x.min(initial=0)) >= -(1 << (left_bits - 1))
             and int(x.max(initial=0)) < 1 << (left_bits - 1), "declared left operand width")
        # alpha UQ31 includes 2**31. The explicit U32 coefficient is lowered
        # with the producer's declared representation, not silently signed S32.
        limit = (1 << right_bits) if y.dtype.kind == "u" else (1 << (right_bits - 1))
        need(int(y.min(initial=0)) >= (0 if y.dtype.kind == "u" else -limit)
             and int(y.max(initial=0)) < limit, "declared right operand width")
        count = int(np.prod(np.broadcast_shapes(x.shape, y.shape)))
        self.ops[f"multiply_{left_bits}x{right_bits}"] += count
        return x.astype(np.int64) * y.astype(np.int64)

    def add(self, a, b):
        x, y = np.asarray(a), np.asarray(b)
        need(magnitude(x) + magnitude(y) <= I64, "I64 add bound")
        self.ops["add_i64"] += int(np.prod(np.broadcast_shapes(x.shape, y.shape)))
        return x.astype(np.int64) + y.astype(np.int64)

    def shift(self, a, shift):
        x = np.asarray(a).astype(np.int64)
        s = int(shift)
        magnitude(x)
        need(-127 <= s <= 255, "bounded runtime shift")
        self.ops["rne_i64"] += x.size
        if s < 0:
            need(magnitude(x) * (1 << -s) <= I64, "I64 left shift bound")
            return x * (1 << -s)
        if s > 63:
            return np.zeros_like(x)
        if s == 0:
            return x.copy()
        # Floor quotient / nonnegative remainder differs from producer's
        # magnitude-based algorithm, and handles negative half-way cases.
        q, r = np.divmod(x, 1 << s)
        half = 1 << (s - 1)
        return q + ((r > half) | ((r == half) & ((q & 1) != 0)))

    def scaled(self, a, b, fraction):
        return self.shift(self.multiply(a, b), fraction)

    def norm(self, x, gamma, epsilon):
        x, g = np.asarray(x), np.asarray(gamma)
        need(x.ndim == 2 and g.shape == (x.shape[1],), "complete norm group")
        answer = np.empty(x.shape, np.int64)
        for row_id, row in enumerate(x):
            total = sum(int(v) ** 2 for v in row)
            need(total < 1 << 128, "U128 sumsq")
            mean = total // len(row) + int(epsilon)
            radicand = mean << 40
            denominator = isqrt_bits(radicand, 128)
            need(denominator > 0, "nonzero norm denominator")
            self.ops["norm_square32"] += len(row)
            self.ops["norm_add128"] += len(row) - 1
            self.ops["division128"] += len(row) + 1
            self.ops["isqrt128"] += 1
            for j, v in enumerate(row):
                numerator = int(v) * int(g[j]) * (1 << 12)
                need(abs(numerator) < 1 << 128, "I128 norm numerator")
                answer[row_id, j] = divided_rne(numerator, denominator, 128)
        return i32(answer)

    def linear(self, x, w, mantissa, exponents):
        x, w = np.asarray(x), np.asarray(w)
        need(x.ndim == w.ndim == 2 and x.shape[1] == w.shape[1]
             and w.dtype == np.int8 and magnitude(w) <= 127, "complete W8 matrix")
        aa, shifts = [], []
        for row in x:
            shift = 0
            while magnitude(self.shift(row, shift)) > 127:
                shift += 1
            aa.append(self.shift(row, shift).astype(np.int8))
            shifts.append(shift)
        aa = np.asarray(aa, np.int8)
        delta = np.asarray(shifts, np.int16)
        need(x.shape[1] * 127 * 127 <= (1 << 31) - 1, "all-prefix INT32 bound")
        acc = aa.astype(np.int64) @ w.astype(np.int64).T
        self.ops["matrix_s8_mac"] += x.shape[0] * w.shape[0] * x.shape[1]
        result = np.empty(acc.shape, np.int64)
        for row in range(len(acc)):
            product = self.multiply(acc[row], mantissa)
            for col in range(w.shape[0]):
                result[row, col] = self.shift(product[col:col + 1],
                                               31 - int(exponents[col]) - int(delta[row]))[0]
        return i32(result), aa, delta, i32(acc)

    def silu(self, x, table, counts):
        x = np.asarray(x)
        lo, hi = -(32 << 12), 32 << 12
        index = self.shift(np.minimum(hi, np.maximum(lo, x)) - lo, 4)
        result = np.asarray(table)[index]
        below, above = x < lo, x > hi
        counts["silu_negative_asymptote"] += int(np.count_nonzero(below))
        counts["silu_positive_identity"] += int(np.count_nonzero(above))
        self.ops["silu_lut_reads32"] += x.size
        return i32(np.where(below, 0, np.where(above, x, result)))

    def coefficients(self, p, c, spec):
        h, d, n, inner = (int(spec[k]) for k in ("heads", "head_dim", "state_size", "inner"))
        history = np.zeros((inner + 2 * n, 4), np.int64)
        convolution, counts = [], Counter()
        for row in p[:, inner:2 * inner + 2 * n]:
            history = np.concatenate((history[:, 1:], row[:, None]), axis=1)
            products = self.multiply(history, c["conv_weight_q20"])
            need(magnitude(products) * 4 <= I64, "conv full-K sum bound")
            z = self.shift(np.sum(products, axis=1), 20) + c["conv_bias_q12"]
            self.ops["conv_add64"] += len(z) * 3
            convolution.append(self.silu(i32(z), c["silu_lut_q12"], counts))
        conv = np.asarray(convolution, np.int32)
        raw_dt = p[:, 2 * inner + 2 * n:].astype(np.int64) + c["dt_bias_q12"]
        lo, hi = -(32 << 12), 32 << 12
        counts["dt_domain_clips"] = int(np.count_nonzero((raw_dt < lo) | (raw_dt > hi)))
        indices = self.shift(np.minimum(hi, np.maximum(lo, raw_dt)) - lo, 4)
        dt = np.asarray([[c["dt_lut_q20"][head, indices[t, head]] for head in range(h)] for t in range(len(p))])
        alpha = np.asarray([[c["alpha_lut_q31"][head, indices[t, head]] for head in range(h)] for t in range(len(p))], np.uint32)
        self.ops["dt_lut_reads32"] += dt.size
        self.ops["alpha_lut_reads32"] += alpha.size
        return {"gate_q12": i32(p[:, :inner]), "conv_q12": conv,
                "conv_history_final_q12": i32(history),
                "x_q12": conv[:, :inner].reshape(-1, h, d),
                "b_q12": conv[:, inner:inner + n], "c_q12": conv[:, inner + n:inner + 2 * n],
                "dt_q20": i32(dt), "alpha_q31": alpha, "counts": counts}

    def proposal(self, state, units, alpha, dt, x, b):
        # Alpha's explicit UQ31 encoding may include 2**31. See compiler
        # contract and the checked U32 right operand in multiply().
        decay = self.shift(self.multiply(state, alpha[:, None, None]), 31)
        dtb = self.shift(self.multiply(dt[:, None], b[None, :]), 12)
        # Compiler/runtime contract requires the intermediate to fit S32.
        dtb = i32(dtb)
        raw = self.multiply(x[:, :, None], dtb[:, None, :])
        injection = np.empty_like(raw)
        for head in range(len(units)):
            injection[head] = self.shift(raw[head], 32 + int(units[head]))
        p = self.add(decay, injection)
        return p, {"dtb_q20_sha256": array_hash(dtb),
                   "injection_sha256": array_hash(injection), "decay_sha256": array_hash(decay),
                   "proposal_sha256": array_hash(p)}


def checkpoint(state, units, epoch, position, contract):
    record = {"state_sha256": array_hash(state), "units": [int(x) for x in units],
              "epoch": int(epoch), "position": int(position), "version": int(position),
              "contract": contract}
    record["checksum"] = hashlib.sha256(json.dumps(record, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return record


def scan(engine, coeff, units, skip, bits, policy, transactions):
    x, b, c, dt, alpha = (coeff[k] for k in ("x_q12", "b_q12", "c_q12", "dt_q20", "alpha_q31"))
    length, heads, dim = x.shape
    n = b.shape[1]
    dtype = np.int16 if bits == 16 else np.int32
    state = np.zeros((heads, dim, n), np.int64)
    units = np.asarray(units, np.int64).copy()
    lo, hi = -(1 << (bits - 1)), (1 << (bits - 1)) - 1
    epoch = position = saturations = 0
    outputs, unit_history, state_hashes, events = [], [units.copy()], [array_hash(state.astype(dtype))], []
    contract = {"bits": bits, "policy": policy, "heads": heads, "dim": dim, "n": n,
                "injection": "dt20*B12_RNE12_then_x12_RNE(32+state_exp)", "maximum_retries": 8}
    need(transactions["contract"] == contract, "state contract")
    for token in range(length):
        need(token < len(transactions["tokens"]), "transaction token missing")
        actual = transactions["tokens"][token]
        before = checkpoint(state.astype(dtype), units, epoch, position, contract)
        need(actual["token"] == token and actual["before"] == before, "state before/owner epoch")
        trial, trial_units, trial_epoch = state.copy(), units.copy(), epoch
        accepted = False
        for attempt in range(9):
            need(attempt < len(actual["attempts"]), "attempt missing")
            record = actual["attempts"][attempt]
            need(record["attempt"] == attempt and record["trial_old_sha256"] == array_hash(trial)
                 and record["trial_units"] == trial_units.tolist() and record["trial_epoch"] == trial_epoch,
                 "causal trial generation")
            p, stages = engine.proposal(trial, trial_units, alpha[token], dt[token], x[token], b[token])
            need(record.get("wide_error") is None and record["stage_hashes"] == stages,
                 "independent complete state proposal")
            count = np.count_nonzero((p < lo) | (p > hi), axis=(1, 2))
            need(record["range_violations"] == count.tolist(), "range guard counts")
            if not count.any() or policy == "static_sat":
                new = np.minimum(hi, np.maximum(lo, p))
                product = engine.multiply(new, c[token][None, None, :])
                need(magnitude(product) * n <= I64, "readout complete-N bound")
                sums = np.sum(product, axis=2)
                out = np.empty_like(sums)
                for head in range(heads):
                    out[head] = engine.shift(sums[head], -int(trial_units[head]))
                out = i32(engine.add(out, engine.scaled(x[token], skip[:, None], 20)))
                need(record["result"] == "COMMIT" and record["published"] is True,
                     "only accepted state published")
                need(len(actual["attempts"]) == attempt + 1, "no work after commit")
                saturations += int(np.count_nonzero(new != p))
                state, units, epoch, position = new, trial_units, trial_epoch, position + 1
                outputs.append(out.reshape(-1))
                unit_history.append(units.copy())
                state_hashes.append(array_hash(state.astype(dtype)))
                accepted = True
                break
            need(record["result"] == "ABORT" and record["published"] is False,
                 "failed proposal unpublished")
            if policy != "guard_rescale" or attempt == 8:
                need(len(actual["attempts"]) == attempt + 1, "rejected token stops")
                break
            for head in np.flatnonzero(count):
                old_hash = array_hash(trial[head])
                trial[head] = engine.shift(trial[head], 1)
                trial_units[head] += 1
                events.append({"token": token, "attempt": attempt, "head": int(head),
                               "old_sha256": old_hash, "new_sha256": array_hash(trial[head]),
                               "new_unit_exponent": int(trial_units[head]), "published": False})
            trial_epoch += 1
        after = checkpoint(state.astype(dtype), units, epoch, position, contract)
        need(actual["committed"] is accepted and actual["after"] == after,
             "atomic state/units/epoch/position/version publication")
        if not accepted:
            need(before == after and len(transactions["tokens"]) == token + 1,
                 "abort leaves published generation unchanged")
            break
    need(transactions["state_sha256"] == state_hashes and transactions["rescale_events"] == events,
         "complete state/checkpoint history")
    for saved in transactions["checkpoints"]:
        p = int(saved["position"])
        need(0 < p <= position and saved == transactions["tokens"][p - 1]["after"],
             "serialized continuous checkpoint")
    return {"output": np.asarray(outputs, np.int32).reshape(-1, heads * dim),
            "initial": np.zeros(state.shape, dtype=dtype), "final": state.astype(dtype),
            "units": np.asarray(unit_history, np.int16), "committed": position,
            "saturations": saturations, "rescale_events": len(events), "epoch": epoch}


def audit_runtime_source(path):
    tree = ast.parse(Path(path).read_text(encoding="utf-8-sig"))
    forbidden = {"float", "exp", "exp2", "sqrt", "rsqrt", "log", "log2", "softmax", "sigmoid", "float16", "float32", "float64"}
    for node in ast.walk(tree):
        need(not isinstance(node, ast.Div), "runtime true division FP bridge")
        if isinstance(node, ast.Constant):
            need(not isinstance(node.value, float), "runtime floating literal")
        if isinstance(node, ast.Call):
            name = node.func.id if isinstance(node.func, ast.Name) else node.func.attr if isinstance(node.func, ast.Attribute) else ""
            need(name not in forbidden, "runtime floating call " + name)
    return {"runtime_source_sha256": sha(path), "ast_no_float_bridge": True,
            "limits": "Source audit is bounded to frozen falcon_int.py; no native kernel or hardware proof"}


def equal_array(expected, actual, name):
    need(expected.shape == actual.shape and expected.dtype == actual.dtype
         and np.array_equal(expected, actual), "integer stage " + name)


def verify(result, compiled, capture, chain_source, int_source):
    result, compiled, capture = Path(result), Path(compiled), Path(capture)
    man, checked = verify_manifest(result, statuses=("EXECUTED",))
    cm, cc = verify_manifest(compiled, statuses=("EXECUTED",))
    capture_manifest, capture_checked = verify_manifest(capture, statuses=("EXECUTED",))
    need(man["schema"] == "falcon-integer-closure-run-v1"
         and cm["schema"] == "falcon-integer-compiler-v1", "Falcon artifact schema")
    for m in (man, cm):
        need(m["producer_sha256"] == sha(chain_source) and m["integer_source_sha256"] == sha(int_source)
             and m["source"]["falcon_chain_sha256"] == sha(chain_source)
             and m["source"]["falcon_int_sha256"] == sha(int_source), "Falcon producer binding")
    source_audit = audit_runtime_source(int_source)
    spec = load_json(compiled / "spec.json")
    need(capture_manifest["schema"] == "falcon-closure-capture-v1"
         and spec["source_capture_manifest_sha256"] == sha(capture / "manifest.json")
         and spec["source_capture_npz_sha256"] == sha(capture / "capture.npz"),
         "real capture/source binding")
    const, inputs = load_arrays(compiled / "constants.npz"), load_arrays(compiled / "inputs.npz")
    captured = load_arrays(capture / "capture.npz")
    # Fixed external cuts are allowed compiler bridges, and must preserve the
    # exact real captured sequence rather than substituting favorable inputs.
    for split_name in ("calibration", "evaluation"):
        need(np.array_equal(inputs[split_name + ".tokens"], captured[split_name + ".tokens"]),
             "frozen calibration/evaluation tokens")
        for suffix in ("input", "attention", "projected"):
            source_value = captured[split_name + "." + suffix].astype(np.float64)
            encoded = np.rint(source_value * (1 << 12))
            need(np.isfinite(encoded).all() and encoded.min(initial=0) >= -(1 << 31)
                 and encoded.max(initial=0) < 1 << 31, "compiler external cut representable")
            equal_array(encoded.astype(np.int32), inputs[split_name + "." + suffix + "_q12"],
                        "real external cut " + split_name + "." + suffix)
    need(len(inputs["calibration.tokens"]) == 16 and len(inputs["evaluation.tokens"]) == 72
         and inputs["calibration.tokens"].tolist() != inputs["evaluation.tokens"][:16].tolist(),
         "calibration/evaluation separation")
    z, report, txn = load_arrays(result / "runtime.npz"), load_json(result / "report.json"), load_json(result / "transactions.json")
    need(report["compiled_manifest_sha256"] == sha(compiled / "manifest.json"), "compiled input binding")
    need(all(v.dtype.kind in "iu" for v in list(z.values()) + list(const.values()) + list(inputs.values())),
         "all runtime/constant/input arrays integer")
    need((spec["heads"], spec["head_dim"], spec["state_size"], spec["inner"], spec["hidden"])
         == (32, 128, 256, 4096, 2560), "complete Falcon shape")
    need(spec["data_format"] == {"storage": "I32", "fraction": 12}
         and spec["runtime_no_float"] is True, "candidate fixed format")
    split, mode, bits, policy = (report[k] for k in ("split", "mode", "state_bits", "policy"))
    need(split in ("calibration", "evaluation") and mode in ("state", "full")
         and bits in (16, 32) and policy in ("static_sat", "static_guard", "guard_rescale"), "run condition")
    eng, trace = Replay(), {}
    x, attention = inputs[split + ".input_q12"], inputs[split + ".attention_q12"]
    trace.update(input_q12=x, external_attention_q12=attention)
    equal_array(x, z["input_q12"], "real input cut")
    equal_array(attention, z["external_attention_q12"], "real attention cut")
    if mode == "full":
        norm = eng.norm(x, const["input_gamma_q20"], spec["epsilon_q24"])
        trace["input_norm_q12"] = norm
        scaled = i32(eng.scaled(norm, const["ssm_in_multiplier_q20"], 20))
        trace["mamba_input_q12"] = scaled
        p, a, delta, acc = eng.linear(scaled, const["in_weight_w8"], const["in_scale_q31"], const["in_scale_exp"])
        p = i32(eng.add(p, const["in_bias_q12"]))
        trace.update(in_a8=a, in_a8_delta=delta, in_acc32=acc, in_linear_q12=p)
        p = i32(eng.scaled(p, const["mup_q20"], 20))
    else:
        p = inputs[split + ".projected_q12"]
        trace["external_native_projected_q12"] = p
    trace["projected_q12"] = p
    coeff = eng.coefficients(p, const, spec)
    trace.update({k: v for k, v in coeff.items() if k != "counts"})
    state = scan(eng, coeff, const[f"state_s{bits}_exponents"], const["skip_q20"], bits, policy, txn)
    trace.update(state_initial=state["initial"], state_final=state["final"], state_units_trace=state["units"], scan_q12=state["output"])
    count = state["committed"]
    if count:
        gated = i32(eng.scaled(state["output"], eng.silu(coeff["gate_q12"][:count], const["silu_lut_q12"], coeff["counts"]), 12))
        trace["gated_q12"] = gated
        normed = eng.norm(gated, const["gated_gamma_q20"], spec["epsilon_q24"])
        trace["gated_norm_q12"] = normed
        y, a, delta, acc = eng.linear(normed, const["out_weight_w8"], const["out_scale_q31"], const["out_scale_exp"])
        y = i32(eng.add(y, const["out_bias_q12"]))
        trace.update(out_a8=a, out_a8_delta=delta, out_acc32=acc, out_linear_q12=y)
        mamba = i32(eng.scaled(y, const["ssm_out_multiplier_q20"], 20))
        attn = i32(eng.scaled(attention[:count], const["attention_out_multiplier_q20"], 20))
        trace.update(mamba_scaled_q12=mamba, attention_scaled_q12=attn)
        joined = i32(eng.add(eng.add(x[:count], mamba), attn))
        trace["join_q12"] = joined
        trace["next_norm_q12"] = eng.norm(joined, const["next_gamma_q20"], spec["epsilon_q24"])
    need(set(trace) == set(z), "complete exact runtime stage index")
    for name in trace:
        equal_array(trace[name], z[name], name)
    need(report["committed_tokens"] == count and report["input_tokens"] == len(x)
         and report["published_state_saturations"] == state["saturations"]
         and report["rescale_events"] == state["rescale_events"]
         and report["final_epoch"] == state["epoch"], "run outcome counters")
    need(report["nonlinear_counts"] == dict(coeff["counts"]), "LUT domain/asymptote counters")
    need(report["status"] == ("EXECUTED_COMPLETE" if count == len(x) else "EXECUTED_REJECTED_PREFIX"), "qualification remains bounded")
    lut_bytes = sum(v.nbytes for name, v in const.items() if "lut" in name)
    need(lut_bytes == spec["nonlinear_lut"]["rom_payload_bytes"]
         == report["actual_payload"]["lut_rom_payload_bytes"], "actual LUT ROM payload")
    return {"status": "PASS", "mode": mode, "split": split, "state_bits": bits, "policy": policy,
            "committed_tokens": count, "input_tokens": len(x), "published_state_saturations": state["saturations"],
            "rescale_events": state["rescale_events"], "final_epoch": state["epoch"],
            "integer_stages_checked": len(trace), "state_attempts_checked": sum(len(t["attempts"]) for t in txn["tokens"]),
            "runtime_source_audit": source_audit, "independent_operation_inventory": dict(eng.ops),
            "artifacts": checked, "compiled_artifacts": cc, "capture_artifacts": capture_checked,
            "limits": ["Integer software oracle and declared source audit; no native INT8 kernel, hardware speed, RTL/PPA or application-quality acceptance",
                       "Native attention and residual external-cut encoding remain; state mode additionally bypasses integer in-projection",
                       "Compiler FP-to-integer encoding/LUT construction is separately declared and not certified by runtime trace alone"]}


def semantic_negatives(result, compiled, capture, chain_source, int_source, out):
    receipts = []
    for name in ("runtime_code", "commit_epoch", "initial_unit"):
        case = Path(out) / ("negative-" + name)
        case.mkdir()
        mutated = case / "result"
        shutil.copytree(result, mutated)
        used_compiled = Path(compiled)
        if name == "runtime_code":
            values = load_arrays(mutated / "runtime.npz")
            values["input_q12"][0, 0] ^= 1
            np.savez_compressed(mutated / "runtime.npz", **values)
            replace_artifact_hash(mutated, "runtime.npz")
        elif name == "commit_epoch":
            txn = load_json(mutated / "transactions.json")
            txn["tokens"][0]["after"]["epoch"] += 1
            save_json(mutated / "transactions.json", txn)
            replace_artifact_hash(mutated, "transactions.json")
        else:
            used_compiled = case / "compiled"
            shutil.copytree(compiled, used_compiled)
            values = load_arrays(used_compiled / "constants.npz")
            report = load_json(mutated / "report.json")
            values[f"state_s{report['state_bits']}_exponents"][0] += 1
            np.savez_compressed(used_compiled / "constants.npz", **values)
            replace_artifact_hash(used_compiled, "constants.npz")
            report["compiled_manifest_sha256"] = sha(used_compiled / "manifest.json")
            save_json(mutated / "report.json", report)
            replace_artifact_hash(mutated, "report.json")
        verify_manifest(mutated, statuses=("EXECUTED",))
        verify_manifest(used_compiled, statuses=("EXECUTED",))
        try:
            verify(mutated, used_compiled, capture, chain_source, int_source)
        except (ValueError, AssertionError) as error:
            receipts.append({"case": name, "artifact_hashes_rewritten": True,
                             "artifact_hash_layer_passed": True, "semantic_rejected": True,
                             "reason": str(error), "mutated_manifest": descriptor(mutated / "manifest.json")})
        else:
            raise ValueError("semantic negative accepted: " + name)
    return receipts


def main():
    p = argparse.ArgumentParser(__doc__)
    for name in ("result", "compiled", "capture", "chain-source", "int-source", "binding", "out"):
        p.add_argument("--" + name, type=Path, required=True)
    p.add_argument("--skip-negatives", action="store_true")
    args = p.parse_args()
    need(not args.out.exists(), "refuse output overwrite")
    binding = load_json(args.binding)
    for name in ("receive_falcon", "audit_io", "integer_oracle"):
        need(binding.get(name + "_sha256") == sha(Path(__file__).with_name(name + ".py")), "receiver dependency " + name)
    args.out.mkdir(parents=True)
    receipt = verify(args.result, args.compiled, args.capture, args.chain_source, args.int_source)
    receipt.update(receiver=binding, producer_manifest=descriptor(args.result / "manifest.json"))
    receipt["semantic_negatives"] = [] if args.skip_negatives else semantic_negatives(
        args.result, args.compiled, args.capture, args.chain_source, args.int_source, args.out)
    if args.skip_negatives:
        receipt["status"] = "PARTIAL_NO_NEGATIVES"
    save_json(args.out / "receipt.json", receipt)
    print(receipt["status"], receipt["committed_tokens"], flush=True)


if __name__ == "__main__":
    main()
