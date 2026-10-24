"""Independent Issue66 state receiver; never imports producer arithmetic.

Uses Python integers for every recurrent multiply/sum/RNE/saturation and Fraction
for independent tie checks/output witnesses. Native convolution/gate/R paths
remain floating reference checks; they are not integer hardware qualification.
"""
import argparse
import copy
import hashlib
import io
import json
import math
from collections import Counter
from fractions import Fraction
from decimal import Decimal, localcontext, ROUND_HALF_EVEN
from pathlib import Path
import shutil
import time
import zipfile

import numpy as np


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"),
                      parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))


def save_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
                          encoding="utf-8")


def manifest(folder, only=None):
    folder = Path(folder)
    value = read_json(folder / "manifest.json")
    if value.get("status") != "PASS":
        raise ValueError("source execution not PASS")
    checked = {}
    for name, wanted in value.get("artifacts", {}).items():
        if only is not None and name not in only:
            continue
        path = folder / name
        if Path(name).is_absolute() or ".." in Path(name).parts:
            raise ValueError("unsafe artifact name")
        actual = dict(bytes=path.stat().st_size, sha256=sha(path))
        if actual != {"bytes": wanted["bytes"], "sha256": wanted["sha256"]}:
            raise ValueError("artifact SHA/size " + name)
        checked[name] = actual
    return value, checked


def close(actual, wanted, label, atol=1e-4, rtol=1e-4):
    a, b = np.asarray(actual, np.float64), np.asarray(wanted, np.float64)
    if a.shape != b.shape or not (np.isfinite(a).all() and np.isfinite(b).all()):
        raise AssertionError("shape/nonfinite " + label)
    if not np.allclose(a, b, atol=atol, rtol=rtol):
        raise AssertionError("floating reference " + label)
    return dict(max_abs=float(np.max(np.abs(a - b))),
                relative_l2=float(np.linalg.norm(a - b) / max(np.linalg.norm(b), 1e-30)))


def raw_capture(folder):
    meta, receipts = manifest(folder, only={"state-raw.npz", "tokens.json"})
    if set(receipts) != {"state-raw.npz", "tokens.json"}:
        raise ValueError("capture must index raw state and exact token IDs")
    if meta.get("state", {}).get("value_heads") != [0, 1]:
        raise ValueError("expected shared key0/value0,1 capture")
    if meta["implementation"]["sha256"] != "b4b17fe08d8d54da34a0fce78639666279ae7fd0a9e4ec06fce6602774707ca3":
        raise ValueError("native implementation changed")
    with np.load(Path(folder) / "state-raw.npz", allow_pickle=False) as z:
        raw = {k: z[k] for k in z.files}
    channels = np.r_[np.arange(128), np.arange(2048, 2176), np.arange(4096, 4352)]
    if not np.array_equal(raw["conv.channel_indices"], channels):
        raise ValueError("conv/key-sharing channel map")
    if raw["weight.conv"].shape != (512, 4):
        raise ValueError("conv kernel shape")
    checks = {}
    for name in ("calibration", "evaluation"):
        pre = name + "."
        shapes = {"query": (1, 32, 2, 128), "key": (1, 32, 2, 128),
                  "value": (1, 32, 2, 128), "g": (1, 32, 2), "beta": (1, 32, 2),
                  "initial_state": (1, 2, 128, 128), "final_state": (1, 2, 128, 128),
                  "state_boundaries": (33, 1, 2, 128, 128),
                  "conv.input": (1, 512, 32), "conv.output": (1, 512, 32),
                  "conv.boundaries": (33, 1, 512, 4),
                  "gate_raw.a": (32, 2), "gate_raw.b": (32, 2)}
        for field, shape in shapes.items():
            a = raw[pre + field]
            if a.shape != shape or a.dtype != np.float32 or not np.isfinite(a).all():
                raise ValueError("raw shape/dtype " + pre + field)
        for field in ("query", "key"):
            x = raw[pre + field]
            if not np.array_equal(x[:, :, 0], x[:, :, 1]):
                raise AssertionError("shared Q/K " + pre + field)
        states = raw[pre + "state_boundaries"][:, 0]
        if (not np.array_equal(states[0], raw[pre + "initial_state"][0])
                or not np.array_equal(states[-1], raw[pre + "final_state"][0])):
            raise AssertionError("actual initial/final boundary identity")
        if not np.any(states[0]):
            raise AssertionError("lost actual nonzero initial state")
        histories = raw[pre + "conv.boundaries"][:, 0]
        current = raw[pre + "conv.input"][0]
        observed = raw[pre + "conv.output"][0]
        max_conv = 0.0
        for t in range(32):
            want_history = np.concatenate([histories[t, :, 1:], current[:, t:t + 1]], axis=1)
            if not np.array_equal(want_history, histories[t + 1]):
                raise AssertionError("conv true history continuity step " + str(t))
            total = np.sum(want_history.astype(np.float64) * raw["weight.conv"].astype(np.float64), axis=1)
            silu = total / (1 + np.exp(-total))
            metric = close(silu, observed[:, t], pre + "convSiLU step" + str(t))
            max_conv = max(max_conv, metric["max_abs"])
        expected_q = np.repeat(observed[:128].T[:, None, :], 2, axis=1)
        expected_k = np.repeat(observed[128:256].T[:, None, :], 2, axis=1)
        expected_v = observed[256:].T.reshape(32, 2, 128)
        for field, expected in (("query", expected_q), ("key", expected_k), ("value", expected_v)):
            if not np.array_equal(raw[pre + field][0], expected):
                raise AssertionError("actual after-conv ingress " + field)
        a = raw[pre + "gate_raw.a"].astype(np.float64) + raw["weight.dt_bias"].astype(np.float64)
        softplus = np.maximum(a, 0) + np.log1p(np.exp(-np.abs(a)))
        expected_g = -np.exp(raw["weight.A_log"].astype(np.float64)) * softplus
        expected_beta = 1 / (1 + np.exp(-raw[pre + "gate_raw.b"].astype(np.float64)))
        gmetric = close(expected_g, raw[pre + "g"][0], pre + "g compiler")
        bmetric = close(expected_beta, raw[pre + "beta"][0], pre + "beta compiler")
        native = native_recurrence(raw, name)
        checks[name] = dict(real_conv_boundaries=33, conv_shift_append_exact=32,
                            shared_qk_heads_exact=True, conv_FP64_reference_maxabs=max_conv,
                            g_FP64_bridge=gmetric, beta_FP64_bridge=bmetric, recurrent_native=native)
    return raw, dict(manifest_sha256=sha(Path(folder) / "manifest.json"),
                     artifacts=receipts, checks=checks,
                     scope="FP64/native references and exact captured continuity; not integer conv/nonlinearity hardware")


def consumer_capture(folder):
    """Lightweight source topology check; never redoes the large down GEMM."""
    meta, checked = manifest(folder, only={"consumer-raw.npz"})
    chain = meta["chain"]
    if (chain["from_layer"] != 3 or chain["to_layer"] != 4
            or chain["hidden_size"] != 2560 or chain["next_projection_outputs"] != 16
            or chain["next_projection_native_outputs"] != 8192
            or chain["norm_weight_contract"] != "effective gamma=1+stored weight"):
        raise ValueError("actual consumer topology")
    results = {}
    with np.load(Path(folder) / "consumer-raw.npz", allow_pickle=False) as z:
        gamma = 1 + z["weight.next_norm"].astype(np.float64)
        weights = z["weight.next_projection"].astype(np.float64)
        if gamma.shape != (2560,) or weights.shape != (16, 2560):
            raise ValueError("consumer source weights")
        for name, rows in (("calibration", 16), ("prefill", 8), ("decode", 32)):
            down, residual, total, norm = (z[name + "." + field]
                                          for field in ("down", "residual", "sum", "norm"))
            if any(a.shape != (rows, 2560) or a.dtype != np.float32 for a in (down, residual, total, norm)):
                raise ValueError("complete hidden source shape/dtype")
            if not np.array_equal(down + residual, total):
                raise AssertionError("real down/residual/next-norm topology")
            a = total.astype(np.float64)
            rms = a / np.sqrt(np.mean(a * a, axis=1, keepdims=True) + 1e-6)
            expected_norm = rms * gamma
            nmetric = close(expected_norm, norm, name + "fullhidden zero-centered RMS")
            expected_projection = norm.astype(np.float64) @ weights.T
            pmetric = close(expected_projection, z[name + ".projection"], name + "first16 next projection")
            results[name] = dict(rows=rows, complete_hidden_values=total.size,
                                 FP32_residual_add_exact=True, full_hidden_RMS_FP64=nmetric,
                                 next_projection16_FP64=pmetric)
    return dict(artifacts=checked, cases=results,
                scope="actual residual/zero-centered fullhidden RMS/next projection16 source check; no large down GEMM, quantized consumer, complete8192 GDN projection or integer norm")


def normalized_source(raw, name):
    pre = name + "."
    q = raw[pre + "query"][0].astype(np.float64)
    k = raw[pre + "key"][0].astype(np.float64)
    # Scalar fsum/sqrt avoids the producer's vector reduction implementation.
    for x, scale in ((q, math.sqrt(128)), (k, 1.0)):
        for t in range(32):
            for h in range(2):
                inv = 1 / math.sqrt(math.fsum(float(v) * float(v) for v in x[t, h]) + 1e-6)
                x[t, h] *= inv / scale
    return q, k


def native_recurrence(raw, name, return_arrays=False):
    pre = name + "."
    q, k = normalized_source(raw, name)
    v = raw[pre + "value"][0].astype(np.float64)
    beta = raw[pre + "beta"][0].astype(np.float64)
    decay = np.exp(raw[pre + "g"][0].astype(np.float64))
    state = raw[pre + "initial_state"][0].astype(np.float64).copy()
    peak_state, peak_output = 0.0, 0.0
    trace, outputs = [state.copy()], []
    for t in range(32):
        state *= decay[t, :, None, None]
        predicted = np.sum(state * k[t, :, :, None], axis=1)
        delta = (v[t] - predicted) * beta[t, :, None]
        state += k[t, :, :, None] * delta[:, None, :]
        y = np.sum(state * q[t, :, :, None], axis=1)
        peak_state = max(peak_state, close(state, raw[pre + "state_boundaries"][t + 1, 0],
                                         pre + "native state step" + str(t))["max_abs"])
        peak_output = max(peak_output, close(y, raw[pre + "output"][0, t],
                                           pre + "native output step" + str(t))["max_abs"])
        trace.append(state.copy())
        outputs.append(y.copy())
    record = dict(steps=32, state_max_abs=peak_state, output_max_abs=peak_output,
                  actual_initial_state_used_once=True)
    return (np.stack(outputs), np.stack(trace), record) if return_arrays else record


def rne(n, shift):
    """Exact signed nearest-even with Python integers, no machine overflow."""
    n, shift = int(n), int(shift)
    if shift <= 0:
        return n << -shift
    sign = -1 if n < 0 else 1
    q, r = divmod(abs(n), 1 << shift)
    half = 1 << (shift - 1)
    return sign * (q + (r > half or (r == half and q & 1)))


def fraction_rne(n, shift):
    f = Fraction(int(n), 1 << shift) if shift >= 0 else Fraction(int(n) << -shift)
    return round(f)


def bit_width(n):
    n = int(n)
    return n.bit_length() + 1 if n >= 0 else (~n).bit_length() + 1


def integer_oracle(q, k, v, beta, decay, initial, eV, eS, lo, hi,
                   wanted_output=None, wanted_states=None, decay_fraction=15):
    """Full32x2x128x128 recurrence oracle; no producer functions or NumPy dots."""
    q, k, v = (np.asarray(x) for x in (q, k, v))
    beta, decay, initial = (np.asarray(x) for x in (beta, decay, initial))
    if q.shape != (32, 2, 128) or k.shape != q.shape or v.shape != q.shape:
        raise ValueError("integer source shape")
    if beta.shape != (32, 2) or decay.shape != beta.shape or initial.shape != (2, 128, 128):
        raise ValueError("integer gates/state shape")
    if decay_fraction not in (15, 31):
        raise ValueError("decay fraction")
    for label, x, lower, upper in (("Q", q, -32767, 32767), ("K", k, -32767, 32767),
                                   ("V", v, -32767, 32767), ("beta", beta, 0, 32768),
                                   ("decay", decay, 0, 1 << decay_fraction), ("state", initial, lo, hi)):
        if not np.issubdtype(x.dtype, np.integer) or np.any(x < lower) or np.any(x > upper):
            raise ValueError("integer dtype/domain " + label)
    states = initial.astype(object).tolist()
    outputs = np.zeros((32, 2, 128), np.int64)
    checkpoints = [initial.astype(np.int64).copy()]
    counts = Counter()
    widths = Counter()
    maxima = Counter()
    def observe(key, value):
        maxima[key] = max(maxima[key], abs(value))
        widths[key] = max(widths[key], bit_width(value))
        if not -(1 << 63) < value < (1 << 63):
            raise OverflowError("producer I64 domain exceeded " + key)
    if wanted_states is not None and not np.array_equal(initial, wanted_states[0]):
        raise AssertionError("integer initial state identity")
    for t in range(32):
        for h in range(2):
            d, b = int(decay[t, h]), int(beta[t, h])
            kk, qq = [int(x) for x in k[t, h]], [int(x) for x in q[t, h]]
            for i in range(128):
                for j in range(128):
                    product = states[h][i][j] * d
                    observe("decay_product", product)
                    states[h][i][j] = rne(product, decay_fraction)
                    observe("decayed_state", states[h][i][j])
                    counts["decay_RNE"] += 1
            for j in range(128):
                p = sum(states[h][i][j] * kk[i] for i in range(128))
                observe("prediction_dot", p)
                predicted = rne(p, 15)
                observe("prediction", predicted)
                vv = rne(int(v[t, h, j]), int(eS[h]) - int(eV[h]))
                observe("aligned_value", vv)
                residual = vv - predicted
                delta_product = residual * b
                delta = rne(delta_product, 15)
                observe("residual", residual)
                observe("beta_product", delta_product)
                observe("correction", delta)
                counts["pred_RNE"] += 1
                counts["delta_RNE"] += 1
                for i in range(128):
                    product = kk[i] * delta
                    update = rne(product, 15)
                    complete = states[h][i][j] + update
                    observe("outer_product", product)
                    observe("state_sum", complete)
                    clipped = max(lo, min(hi, complete))
                    counts["state_saturations"] += clipped != complete
                    states[h][i][j] = clipped
                    counts["outer_RNE"] += 1
                total = sum(states[h][i][j] * qq[i] for i in range(128))
                observe("output_dot", total)
                y = rne(total, 15)
                if not -(1 << 63) <= y < (1 << 63):
                    raise OverflowError("oracle output exceeds artifact I64 container")
                # Every output also uses Fraction, separate from the bit RNE.
                if y != fraction_rne(total, 15):
                    raise AssertionError("Pythonint/Fraction RNE mismatch")
                outputs[t, h, j] = y
                counts["output_Fraction_RNE"] += 1
                if wanted_output is not None and int(wanted_output[t, h, j]) != y:
                    raise AssertionError("integer output oracle step/head/channel " + str((t, h, j)))
        snapshot = np.asarray(states, dtype=np.int64)
        checkpoints.append(snapshot.copy())
        if wanted_states is not None and not np.array_equal(snapshot, wanted_states[t + 1]):
            raise AssertionError("integer state continuity/oracle step " + str(t + 1))
    return outputs, np.stack(checkpoints), dict(counts), dict(maxima), dict(widths)


def boundary_self_checks():
    for shift in range(1, 17):
        half = 1 << (shift - 1)
        for n in (0, 1, -1, half, -half, 3 * half, -3 * half, (1 << 63) - 1, -(1 << 63)):
            if rne(n, shift) != fraction_rne(n, shift):
                raise AssertionError("signed RNE boundary")
    if rne(16384, 15) + rne(16384, 15) == rne(32768, 15):
        raise AssertionError("early partial rounding counterexample lost")
    if 1 + rne(16384, 15) == rne((1 << 15) + 16384, 15):
        raise AssertionError("stage RNE placement counterexample lost")
    return dict(signed_RNE_Fraction_boundaries=144,
                premature_partial_rounding_rejected=True,
                outer_RNE_before_integer_add_distinguished=True)


def exact_bridge(values, exponent, low, high):
    """FP32/dyadic source -> codes using exact Fraction, independent of FP RNE."""
    x = np.asarray(values)
    out = np.empty(x.shape, np.int64)
    for index in np.ndindex(x.shape):
        e = int(exponent[index] if isinstance(exponent, np.ndarray) else exponent)
        a = Fraction.from_float(float(x[index]))
        scaled = a / (1 << e) if e >= 0 else a * (1 << -e)
        out[index] = max(low, min(high, round(scaled)))
    return out


def calibration_units(raw):
    su, vu = [], []
    for h in range(2):
        sm = max(float(np.max(np.abs(raw["calibration.initial_state"][0, h]))),
                 float(np.max(np.abs(raw["calibration.final_state"][0, h]))))
        vm = float(np.max(np.abs(raw["calibration.value"][0, :, h])))
        for maximum, result in ((sm, su), (vm, vu)):
            e = -20 if maximum == 0 else -26
            limit = 2 * Fraction.from_float(maximum)
            while Fraction(32767) * (Fraction(1 << e) if e >= 0 else Fraction(1, 1 << -e)) < limit:
                e += 1
            result.append(e)
    return np.array(su, np.int8), np.array(vu, np.int8)


def source_codes(raw, name, value_units, decay_fraction):
    q, k = normalized_source(raw, name)
    compiled = {}
    for label, value in (("q", q), ("k", k)):
        # This independently recomputes the explicit FP64 normalization bridge.
        compiled[label] = exact_bridge(value, -15, -32767, 32767)
    unit_grid = np.broadcast_to(value_units[None, :, None], (32, 2, 128))
    compiled["v"] = exact_bridge(raw[name + ".value"][0], unit_grid, -32767, 32767)
    compiled["beta"] = exact_bridge(raw[name + ".beta"][0], -15, 0, 32768)
    codes = np.empty((32, 2), np.int64)
    with localcontext() as ctx:
        ctx.prec = 60
        for t in range(32):
            for h in range(2):
                g = Decimal.from_float(float(raw[name + ".g"][0, t, h]))
                value = (g.exp() * Decimal(1 << decay_fraction)).to_integral_value(rounding=ROUND_HALF_EVEN)
                codes[t, h] = max(0, min(1 << decay_fraction, int(value)))
    compiled["decay"] = codes
    return compiled


def semantic_digest(array):
    """Specified commit digest encoding, independently assembled as little-endian."""
    array = np.asarray(array, dtype="<i8", order="C")
    prefix = b"int64" + str(tuple(array.shape)).encode("ascii")
    return hashlib.sha256(prefix + array.tobytes(order="C")).hexdigest()


def json_digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def validate_commits(record, states, outputs, input_manifest_sha):
    fmt = record["format"]
    name = fmt["window"]
    if fmt.get("sequence") != json_digest(dict(source=input_manifest_sha, window=name)):
        raise AssertionError("foreign sequence descriptor")
    if fmt.get("format_epoch") != 0 or fmt.get("head_slots") != [0, 1]:
        raise AssertionError("format epoch/head descriptor")
    contract = json_digest(fmt)
    events = record["execution"]["commits"]
    if len(events) != 32:
        raise AssertionError("missing state commit events")
    for t, event in enumerate(events):
        wanted = dict(version=t + 1, position=129 + t, contract=contract,
                      old_state_sha256=semantic_digest(states[t]),
                      state_sha256=semantic_digest(states[t + 1]),
                      output_sha256=semantic_digest(outputs[t]))
        if event != wanted:
            raise AssertionError("state commit/version/hash continuity step " + str(t))
    if record["execution"].get("final_version") != 32 or record["execution"].get("final_position") != 160:
        raise AssertionError("final state version/position")


def metric(actual, wanted):
    a, b = np.asarray(actual, np.float64), np.asarray(wanted, np.float64)
    return dict(relative_rmse=float(np.linalg.norm(a - b) / max(np.linalg.norm(b), 1e-30)),
                max_abs=float(np.max(np.abs(a - b))))


def verify_integer(folder, capture_folder, raw, limit=None):
    meta, receipts = manifest(folder)
    capture_sha = sha(Path(capture_folder) / "manifest.json")
    state_sha = sha(Path(capture_folder) / "state-raw.npz")
    source = meta["source"]
    if (source["input_manifest_sha256"] != capture_sha
            or source["input_NPZ_sha256"] != state_sha
            or source["input_NPZ_name"] != "state-raw.npz"):
        raise ValueError("integer source/capture binding")
    rows = read_json(Path(folder) / "state-results.json")
    expected_ids = {name + ".S" + str(bits) + ".D" + str(df)
                    for name in ("calibration", "evaluation") for bits in (16, 32) for df in (15, 31)}
    if {row["id"] for row in rows} != expected_ids or len(rows) != 8 or meta["integer_conditions"] != 8:
        raise ValueError("expected new32step/calibration-evaluation/fourprofile matrix")
    su16, vu = calibration_units(raw)
    source_cache, native_cache, checks = {}, {}, []
    for row in rows[:limit] if limit else rows:
        fmt = row["format"]
        name, bits, df = fmt["window"], fmt["state_bits"], fmt["decay_fraction"]
        if row["status"] != "PASS_INTEGER_EXECUTION" or row["integer_steps"] != 32 or row["original_native_steps"] != 32:
            raise ValueError("integer condition incomplete")
        if fmt["QK_unit"] != -15 or fmt["beta_unit"] != -15 or bits not in (16, 32) or df not in (15, 31):
            raise ValueError("integer format contract")
        if fmt["source_input_sha256"] != state_sha:
            raise ValueError("descriptor source NPZ")
        eS = su16.astype(np.int16) - (16 if bits == 32 else 0)
        if fmt["state_unit"] != eS.tolist() or fmt["value_unit"] != vu.tolist():
            raise AssertionError("evaluation-fitted or changed static scale")
        filename = row["artifact"]["name"]
        if receipts.get(filename) != {"bytes": row["artifact"]["bytes"], "sha256": row["artifact"]["sha256"]}:
            raise ValueError("condition artifact binding")
        with np.load(Path(folder) / filename, allow_pickle=False) as z:
            a = {k: z[k] for k in z.files}
        if not np.array_equal(a["state_units"], eS) or not np.array_equal(a["value_units"], vu):
            raise AssertionError("scale artifact")
        key = (name, df)
        if key not in source_cache:
            source_cache[key] = source_codes(raw, name, vu, df)
        encoded = source_cache[key]
        for field in ("q", "k", "v", "beta", "decay"):
            if not np.array_equal(a[field], encoded[field]):
                raise AssertionError("independent bridge code " + field + " " + row["id"])
        lo, hi = (-32768, 32767) if bits == 16 else (-(1 << 31), 32767 << 16)
        initial = exact_bridge(raw[name + ".initial_state"][0],
                               np.broadcast_to(eS[:, None, None], (2, 128, 128)), lo, hi)
        if not np.array_equal(initial, a["state_initial"]):
            raise AssertionError("initial state source encoding")
        if name not in native_cache:
            native_cache[name] = native_recurrence(raw, name, return_arrays=True)
        fy, fs, _ = native_cache[name]
        if not np.array_equal(a["native_output"], raw[name + ".output"][0]):
            raise AssertionError("native output source identity")
        if not np.array_equal(a["native_state_reference"], raw[name + ".state_boundaries"][:, 0]):
            raise AssertionError("native state source identity")
        close(a["FP64_state_reference"], fs, row["id"] + "FP64 oracle", atol=1e-10, rtol=1e-10)
        outputs, states, counts, maxima, widths = integer_oracle(
            a["q"], a["k"], a["v"], a["beta"], a["decay"], a["state_initial"],
            vu, eS, lo, hi, wanted_output=a["output_codes"], wanted_states=a["state_trace"],
            decay_fraction=df)
        validate_commits(row, states, outputs, capture_sha)
        if row["execution"]["saturations"] != counts["state_saturations"]:
            raise AssertionError("state saturation count")
        if row["execution"]["observed_absolute_max"] != maxima:
            raise AssertionError("integer intermediate range statistics")
        physical_y = outputs * np.exp2(eS.astype(np.float64))[None, :, None]
        physical_s = states * np.exp2(eS.astype(np.float64))[None, :, None, None]
        for sample in row["error_by_length"]:
            n = sample["steps"]
            wanted = dict(output_vs_native=metric(physical_y[:n], raw[name + ".output"][0, :n]),
                          state_vs_FP64_replay=metric(physical_s[n], fs[n]),
                          state_vs_native_capture=metric(physical_s[n], raw[name + ".state_boundaries"][n, 0]))
            for field, values in wanted.items():
                for stat, number in values.items():
                    if not math.isclose(number, sample[field][stat], rel_tol=1e-8, abs_tol=1e-10):
                        raise AssertionError("independent diagnostic metric " + field)
        checks.append(dict(id=row["id"], status="PASS", counts=counts,
                           observed_required_signed_bits=widths,
                           output_values=outputs.size, state_values=states.size,
                           commit_events=32, complete_K_before_RNE=True,
                           independent_initial_encoding_values=initial.size,
                           source_bridge_scope="Fraction dyadic source encoding; scalar fsum/sqrt normalization; Decimal60 decay compiler. Floating bridges are not target hardware."))
    return dict(status="PASS", source=source, artifacts=receipts, conditions=checks,
                scope="new capture32/alltwoheads; full Pythonint state/output oracle, not legacy prefix or hardware")


def write_npz(path, arrays):
    with zipfile.ZipFile(path, "x", zipfile.ZIP_DEFLATED) as z:
        for name, array in sorted(arrays.items()):
            buf = io.BytesIO()
            np.save(buf, array, allow_pickle=False)
            info = zipfile.ZipInfo(name + ".npy", (2026, 10, 24, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, buf.getvalue())


def rehashed_negative_integer(source_folder, destination, code_mutation):
    source_folder, destination = Path(source_folder), Path(destination)
    destination.mkdir()
    meta = read_json(source_folder / "manifest.json")
    rows = read_json(source_folder / "state-results.json")
    name = rows[0]["artifact"]["name"]
    for filename in meta["artifacts"]:
        if filename not in (name, "state-results.json"):
            # Read-only hard links avoid duplicating every full trace.
            try:
                (destination / filename).hardlink_to(source_folder / filename)
            except OSError:
                shutil.copyfile(source_folder / filename, destination / filename)
    if code_mutation:
        with np.load(source_folder / name, allow_pickle=False) as z:
            arrays = {k: z[k] for k in z.files}
        arrays["output_codes"][0, 0, 0] += 1
        write_npz(destination / name, arrays)
    else:
        try:
            (destination / name).hardlink_to(source_folder / name)
        except OSError:
            shutil.copyfile(source_folder / name, destination / name)
        rows[0]["execution"]["commits"][8]["old_state_sha256"] = "0" * 64
    desc = dict(bytes=(destination / name).stat().st_size, sha256=sha(destination / name))
    rows[0]["artifact"].update(desc)
    save_json(destination / "state-results.json", rows)
    meta["artifacts"][name] = desc
    meta["artifacts"]["state-results.json"] = dict(bytes=(destination / "state-results.json").stat().st_size,
                                                  sha256=sha(destination / "state-results.json"))
    save_json(destination / "manifest.json", meta)


def negative_checks(integer_folder, capture_folder, raw, out):
    checks = []
    for name, code in (("rehashed-output-code", True), ("rehashed-commit-continuity", False)):
        target = out / name
        rehashed_negative_integer(integer_folder, target, code)
        # Ensure its rewritten SHA/size index is valid before semantic rejection.
        manifest(target)
        try:
            verify_integer(target, capture_folder, raw, limit=1)
        except AssertionError as error:
            expected = "integer output oracle" if code else "state commit/version/hash continuity"
            if expected not in str(error):
                raise
            checks.append(dict(name=name, status="REJECTED_BY_INDEPENDENT_SEMANTICS",
                               error=str(error), rewritten_artifact_SHA_passed=True))
        else:
            raise AssertionError("negative integer artifact accepted " + name)
    target = out / "rehashed-conv-boundary"
    target.mkdir()
    source = Path(capture_folder)
    meta = read_json(source / "manifest.json")
    shutil.copyfile(source / "tokens.json", target / "tokens.json")
    with np.load(source / "state-raw.npz", allow_pickle=False) as z:
        arrays = {k: z[k] for k in z.files}
    arrays["evaluation.conv.boundaries"][10, 0, 0, 0] += 1
    write_npz(target / "state-raw.npz", arrays)
    meta["artifacts"]["state-raw.npz"] = dict(bytes=(target / "state-raw.npz").stat().st_size,
                                               sha256=sha(target / "state-raw.npz"))
    save_json(target / "manifest.json", meta)
    manifest(target, only={"state-raw.npz", "tokens.json"})
    try:
        raw_capture(target)
    except AssertionError as error:
        if "conv true history continuity" not in str(error):
            raise
        checks.append(dict(name="rehashed-conv-boundary", status="REJECTED_BY_INDEPENDENT_SEMANTICS",
                           error=str(error), rewritten_artifact_SHA_passed=True))
    else:
        raise AssertionError("mutated actual conv boundary accepted")
    return checks


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture", type=Path, required=True)
    parser.add_argument("--integer", type=Path)
    parser.add_argument("--repeat", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--no-negatives", action="store_true")
    args = parser.parse_args()
    if args.out.exists():
        raise ValueError("new output directory required")
    begin = time.monotonic()
    raw, source_receipt = raw_capture(args.capture)
    consumer_receipt = consumer_capture(args.capture)
    checks = boundary_self_checks()
    integer = verify_integer(args.integer, args.capture, raw) if args.integer else None
    repeated = None
    if args.repeat:
        if not args.integer:
            raise ValueError("repeat requires integer producer directory")
        _, first = manifest(args.integer)
        _, second = manifest(args.repeat)
        if first != second:
            raise AssertionError("two-round integer artifacts differ")
        repeated = dict(all_artifacts_byte_identical=True,
                        scope="first round arithmetic independently replayed; second complete SHA/size identity verified")
    args.out.mkdir(parents=True)
    negative = negative_checks(args.integer, args.capture, raw, args.out) if args.integer and not args.no_negatives else []
    counts = Counter()
    for row in integer["conditions"] if integer else []:
        counts.update(row["counts"])
    result = dict(status="PASS", receiver_sha256=sha(__file__), capture=source_receipt,
                  consumer_source=consumer_receipt,
                  boundaries=checks, integer=integer, counts=dict(counts), repeat=repeated,
                  negatives=negative, seconds=time.monotonic() - begin,
                  hardware_validated=False, full_model_quality_accepted=False,
                  bridge_scope="Raw norm/SiLU/gates/exp and offline compilers stay explicit floating boundaries; no producer imports or target hardware inference")
    save_json(args.out / "audit.json", result)
    print(json.dumps(dict(status="PASS", conditions=0 if integer is None else len(integer["conditions"]),
                          counts=dict(counts), negatives=len(negative), seconds=result["seconds"])), flush=True)


if __name__ == "__main__":
    main()
