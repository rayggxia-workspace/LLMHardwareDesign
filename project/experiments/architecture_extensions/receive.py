"""Independent, bounded Issue70 mathematical and provenance receiver.

Producer modules are never imported. Python integers are the dot/RNE oracle;
FP64/Decimal state bridges are explicitly separate from integer execution.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil

import numpy as np


def require(ok, text):
    if not ok:
        raise ValueError(text)


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"),
                      parse_constant=lambda s: (_ for _ in ()).throw(ValueError(s)))


def write_json(path, data):
    Path(path).write_text(json.dumps(data, sort_keys=True, indent=2,
                                    allow_nan=False) + "\n", encoding="utf-8")


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for data in iter(lambda: f.read(8 << 20), b""):
            h.update(data)
    return h.hexdigest()


def local_path(root, relative):
    root = Path(root).resolve()
    require(isinstance(relative, str) and relative and "\\" not in relative
            and ":" not in relative, "unsafe artifact path")
    path = (root / relative).resolve()
    require(not Path(relative).is_absolute() and path != root
            and path.is_relative_to(root), "artifact escapes root")
    return path


def artifact(path):
    return dict(bytes=Path(path).stat().st_size, sha256=sha(path))


def manifest(folder):
    """Hash every indexed artifact, not only tensors selected by the oracle."""
    folder = Path(folder)
    m = read_json(folder / "manifest.json")
    require(m.get("status") in ("PASS", "EXECUTED"), "execution manifest not complete")
    entries = m.get("artifacts", {})
    if isinstance(entries, list):
        require(len({x["path"] for x in entries}) == len(entries), "duplicate artifacts")
        entries = {x["path"]: x for x in entries}
    require(isinstance(entries, dict) and len(entries) > 0, "empty artifact index")
    checked = {}
    for name, wanted in entries.items():
        got = artifact(local_path(folder, name))
        require(re.fullmatch("[0-9a-f]{64}", wanted.get("sha256", "")) is not None,
                "malformed artifact SHA " + name)
        require(got == {k: wanted[k] for k in ("bytes", "sha256")},
                "artifact SHA/size " + name)
        checked[name] = got
    return m, checked


def load_npz(path):
    with np.load(path, allow_pickle=False) as z:
        result = {k: z[k] for k in z.files}
    require(not any(a.dtype.hasobject for a in result.values()), "object tensor")
    return result


def rne(value, shift):
    n, s = int(value), int(shift)
    require(-1024 <= s <= 1024, "unbounded shift")
    if s <= 0:
        return n << -s
    sign = -1 if n < 0 else 1
    q, rem = divmod(abs(n), 1 << s)
    return sign * (q + int(2 * rem > 1 << s or (2 * rem == 1 << s and q % 2)))


def scalar(a):
    x = np.asarray(a)
    require(x.size == 1 and np.issubdtype(x.dtype, np.integer), "integer scalar")
    return int(x.reshape(-1)[0])


def verify_dots(z, rows):
    require(len(rows) > 0, "missing complete-dot witnesses")
    checked = 0
    for row in rows:
        a, w = z[row["a"]], z[row["w"]]
        require(a.dtype == np.int8 and w.dtype == np.int8 and a.ndim == w.ndim == 1
                and a.shape == w.shape and a.size > 0, "W8A8 complete dot shape/dtype")
        require(np.all(np.abs(w.astype(np.int16)) <= 127), "symmetric W8 domain")
        total = sum(int(x) * int(y) for x, y in zip(a, w))
        bound = 128 * sum(abs(int(v)) for v in w)
        require(-(1 << 31) <= total < 1 << 31, "dot INT32 overflow")
        require(total == scalar(z[row["acc"]]), "independent dot code")
        # A producer may promise symmetric A8 [-127,127] or full S8. The
        # theoretical bound must be enough for its declared domain.
        amax = int(row.get("activation_abs_max", 127))
        require(amax in (127, 128) and np.all(np.abs(a.astype(np.int16)) <= amax),
                "A8 domain")
        bound = amax * sum(abs(int(v)) for v in w)
        declared = int(row.get("bound", bound))
        require(bound <= declared < (1 << 31), "conditional INT32 bound")
        if "K" in row:
            require(int(row["K"]) == a.size, "complete dot K")
        checked += 1
    return checked


def verify_requants(z, rows):
    require(len(rows) > 0, "missing RNE witnesses")
    checked = 0
    for row in rows:
        value = scalar(z[row["value"]])
        multiplier = scalar(z[row["multiplier"]])
        shift = scalar(z[row["shift"]])
        bits = int(row.get("bits", 8))
        require(bits in (8, 16, 32) and -(1 << 31) <= value < (1 << 31),
                "requant input/bits")
        wide = value * multiplier
        require(-(1 << 63) <= wide < 1 << 63, "requant I64 product")
        rounded = rne(wide, shift)
        low, high = -(1 << (bits - 1)), (1 << (bits - 1)) - 1
        expected = max(low, min(high, rounded))
        require(expected == scalar(z[row["out"]]), "independent requant RNE/saturation")
        if "rounded" in row:
            require(rounded == scalar(z[row["rounded"]]), "requant pre-sat rounded")
        checked += 1
    return checked


def topk(logits, k):
    x = np.asarray(logits, np.float64)
    require(x.ndim == 2 and 0 < k <= x.shape[1] and np.isfinite(x).all(),
            "router logits shape/finite")
    # Fully specified tie rule; never depend on an unstable partial partition.
    return np.array([sorted(range(len(row)), key=lambda i: (-float(row[i]), i))[:k]
                     for row in x], dtype=np.int64)


def verify_routes(z, row):
    fp, quant = z[row["logits_fp"]], z[row["logits_q"]]
    require(fp.shape == quant.shape and fp.shape[1] == 40, "Granite router shape")
    ids_fp, ids_q = topk(fp, 8), topk(quant, 8)
    require(np.array_equal(ids_fp, z[row["ids_fp"]]), "native top8 independently reordered")
    require(np.array_equal(ids_q, z[row["ids_q"]]), "quant top8 must be recomputed")
    changes = sum(set(map(int, a)) != set(map(int, b)) for a, b in zip(ids_fp, ids_q))
    return dict(rows=len(fp), top8_set_flips=changes,
                coefficient_generation="FP64 softmax bridge; not integer exp/div qualification")


def verify_merge(z, row):
    """Whole selected-top8 reduction at one or more token outputs.

    value=code*2**unit. Route weights are nonnegative Qfraction integers;
    all eight products align to minimum unit before one final RNE.
    """
    codes, units, weights = (z[row[k]] for k in ("codes", "units", "weights"))
    require(codes.ndim == 3 and codes.shape[1] == 8 and codes.shape[2] > 0,
            "complete selected-top8 expert codes")
    require(np.issubdtype(codes.dtype, np.integer) and np.issubdtype(units.dtype, np.integer)
            and np.issubdtype(weights.dtype, np.integer), "merge integer dtype")
    require(units.shape in (codes.shape, codes.shape[:2], (codes.shape[0], 8, 1))
            and weights.shape == codes.shape[:2], "merge unit/weight shape")
    unit3 = np.broadcast_to(units[:, :, None] if units.ndim == 2 else units, codes.shape)
    fraction = int(row.get("weight_fraction", 15))
    require(0 < fraction <= 31 and np.all(weights >= 0) and np.all(weights <= 1 << fraction),
            "route coefficient domain")
    expected_sum = np.empty((codes.shape[0], codes.shape[2]), dtype=object)
    expected_unit = np.empty(expected_sum.shape, np.int64)
    for t, j in np.ndindex(expected_sum.shape):
        e = min(int(v) for v in unit3[t, :, j]) - fraction
        total = sum(int(codes[t, i, j]) * int(weights[t, i])
                    * (1 << (int(unit3[t, i, j]) - fraction - e)) for i in range(8))
        require(-(1 << 63) <= total < 1 << 63, "top8 aligned sum I64 range")
        expected_sum[t, j], expected_unit[t, j] = total, e
    require(np.array_equal(expected_sum, z[row["sum"]]), "complete top8 aligned sum")
    require(np.array_equal(expected_unit, z[row["sum_unit"]]), "top8 shared output unit")
    if "out" in row:
        target = np.broadcast_to(z[row["out_unit"]], expected_sum.shape)
        bits = int(row.get("bits", 32))
        low, high = -(1 << (bits - 1)), (1 << (bits - 1)) - 1
        expected = np.empty(expected_sum.shape, np.int64)
        for ix in np.ndindex(expected.shape):
            expected[ix] = max(low, min(high, rne(expected_sum[ix],
                                int(target[ix]) - int(expected_unit[ix]))))
        require(np.array_equal(expected, z[row["out"]]), "top8 output RNE/sat")
    return dict(tokens=codes.shape[0], experts=8, complete_hidden=codes.shape[2],
                aligned_values=expected_sum.size)


def fixed_from_float(value, unit, bits):
    """Independent exact rounding of an already frozen binary FP64 value."""
    require(math.isfinite(float(value)), "nonfinite fixed input")
    n, d = float(value).as_integer_ratio()
    if unit < 0:
        n <<= -unit
    else:
        d <<= unit
    sign = -1 if n < 0 else 1
    q, rem = divmod(abs(n), d)
    rounded = sign * (q + int(2 * rem > d or (2 * rem == d and q % 2)))
    lo, hi = -(1 << (bits - 1)), (1 << (bits - 1)) - 1
    return max(lo, min(hi, rounded)), rounded < lo or rounded > hi


def compare_float(got, expected, label, atol=2e-7, rtol=2e-6):
    a, b = np.asarray(got), np.asarray(expected)
    require(a.shape == b.shape and np.isfinite(a).all() and np.isfinite(b).all(), label + " shape/finite")
    require(np.allclose(a, b, atol=atol, rtol=rtol), label + " independent FP64")
    return float(np.max(np.abs(a - b))) if a.size else 0.0


def verify_granite_merge(z, row):
    """Actual Granite schema: RQ complete top8 to common S32 before Q15 sum."""
    a, m, s, aligned = (z[row[k]] for k in ("acc", "multiplier", "shift", "aligned"))
    require(a.shape == m.shape == s.shape == aligned.shape == (8, 1536),
            "Granite whole 8xH1536 merge")
    require(all(np.issubdtype(x.dtype, np.integer) for x in (a, m, s, aligned)),
            "Granite merge integer formats")
    lo, hi = -(1 << 31), (1 << 31) - 1
    require(np.all((a >= lo) & (a <= hi)), "Granite merge inputs INT32")
    for ix in np.ndindex(a.shape):
        product = int(a[ix]) * int(m[ix])
        require(-(1 << 63) <= product < 1 << 63, "Granite full merge I64 RQ product")
        wanted = max(lo, min(hi, rne(product, int(s[ix]))))
        require(wanted == int(aligned[ix]), "Granite expert common-unit RQ")
    require(int(row["common_unit_exp"]) == scalar(z["common_unit_exp"]),
            "Granite common unit agreement")
    weights = z[row["gate_q15"]]
    require(weights.shape == (8,) and np.issubdtype(weights.dtype, np.integer)
            and np.all((weights >= 0) & (weights <= 32768)), "Granite Q15 gates")
    weighted, out = z[row["weighted_sum"]], z[row["out"]]
    require(weighted.shape == out.shape == (1536,), "Granite complete hidden reduction")
    for j in range(1536):
        total = sum(int(aligned[i, j]) * int(weights[i]) for i in range(8))
        require(-(1 << 63) <= total < 1 << 63, "Granite weighted I64 range")
        require(total == int(weighted[j]), "Granite eight-expert weighted sum")
        require(max(lo, min(hi, rne(total, 15))) == int(out[j]), "Granite final RNE/sat")
    return dict(experts=8, hidden=1536, rq_values=aligned.size,
                final_values=1536, common_unit_exp=int(row["common_unit_exp"]))


def source_commit(m):
    commit = m.get("source", {}).get("commit", "")
    require(re.fullmatch("[0-9a-f]{40}", commit) is not None, "unbound source commit")
    return commit


def check_capture_binding(result, capture):
    wanted = result.get("source", {}).get("capture_manifest_sha256")
    require(wanted == sha(Path(capture) / "manifest.json"), "capture manifest binding")


def granite(result, capture):
    m, files = manifest(result)
    cm, cf = manifest(capture)
    source_commit(m); source_commit(cm)
    check_capture_binding(m, capture)
    require(m.get("kind") == "granite_numeric" and cm.get("kind") == "granite_capture",
            "Granite manifest kinds")
    revision = m.get("model_revision", "")
    require(re.fullmatch("[0-9a-f]{40}", revision) is not None
            and revision == cm.get("model_revision"), "Granite revision binding")
    w = read_json(Path(result) / "witnesses.json")
    z = load_npz(Path(result) / "witnesses.npz")
    require(len(w["dots"]) == len(w["requants"]) == 32 and len(w["routing"]) == 2
            and len(w["merges"]) == 4, "Granite frozen witness count")
    rows = [verify_routes(z, row) for row in w["routing"]]
    merges = [verify_granite_merge(z, row) for row in w["merges"]]
    # Gates are checked from the actual selected FP/quant routes, not merely
    # accepted because the sum agrees with some unrelated eight coefficients.
    for row in w["merges"]:
        activation, route = row["label"].split("__", 1)
        key = "route_weights_fp" if route == "route_fixed_diagnostic" else "route_weights_q_" + activation
        expected = np.rint(z[key][0] * 32768).astype(np.int64)
        require(np.array_equal(expected, z[row["gate_q15"]]), "selected-route gate binding")
    metrics = read_json(Path(result) / "metrics.json")
    cases = metrics["cases"]
    require(len(cases) == 8 and {x["route"] for x in cases} ==
            {"route_fixed_diagnostic", "route_recomputed"}, "Granite route controls")
    for row in w["routing"]:
        for suffix in ("fp", "q"):
            logits = z[row["logits_" + suffix]]
            ids = z[row["ids_" + suffix]]
            selected = np.take_along_axis(logits, ids, axis=1)
            coeff = np.exp(selected - selected.max(axis=1, keepdims=True))
            coeff /= coeff.sum(axis=1, keepdims=True)
            key = "route_weights_fp" if suffix == "fp" else "route_weights_q_" + row["activation"]
            compare_float(coeff, z[key], "Granite selected top8 FP64 softmax", atol=1e-14, rtol=1e-13)
    return dict(model="Granite-3.1-3B-A800M-Instruct", revision=revision,
                source_commit=source_commit(m), result_manifest_sha256=sha(Path(result)/"manifest.json"),
                capture_manifest_sha256=sha(Path(capture)/"manifest.json"),
                artifacts_checked=len(files) + len(cf), dots=verify_dots(z, w["dots"]),
                requants=verify_requants(z, w["requants"]), routing=rows, merges=merges,
                qualification="32 full-K dots and 4 complete top8/H1536 merges; not all layer dots or full-model quality; FP softmax/SiLU/scale bridges remain")


def recurrence(z, prefix, *, bits=None):
    """Independent Mamba2 FP64 bridge and optional fixed integer storage.

    This is deliberately NOT called an integer recurrence. FP coefficients and
    multiplications remain FP64; the store's exact IEEE-value rounding is tested
    separately with Python integers at every step's extrema and boundary cells.
    """
    a, dt, x, b, c = [np.asarray(z[prefix + "." + k], np.float64)
                     for k in ("a", "dt", "x", "b", "c")]
    skip = float(z[prefix + ".skip"])
    T, D, N = len(a), x.shape[1], b.shape[1]
    require(a.shape == dt.shape == (T,) and x.shape == (T, D)
            and b.shape == c.shape == (T, N), "Mamba2 coefficient shape")
    require(all(np.isfinite(v).all() for v in (a, dt, x, b, c)) and math.isfinite(skip)
            and np.all((a >= 0) & (a <= 1)) and np.all(dt >= 0), "Mamba2 coefficient domain")
    state = np.asarray(z[prefix + ".initial_state"], np.float64).copy()
    require(state.shape == (D, N) and np.isfinite(state).all(), "Mamba2 initial state")
    spot = sat_total = 0
    output, states = [], []
    if bits:
        key = "S" + str(bits)
        unit = float(z[key + ".unit"])
        exponent = scalar(z[key + ".unit_exponent"])
        require(math.isfinite(unit) and unit == 2.0 ** exponent and unit > 0,
                "Mamba2 power-of-two state unit")
        calmax = float(np.max(np.abs(z["calibration.fp64_states"])))
        expected_exp = math.ceil(math.log2(max(calmax, 2.0 ** -80) / ((1 << (bits - 1)) - 1)))
        require(exponent == expected_exp, "state scale selected from calibration only")
        codes = z[key + ".codes"]
        require(codes.shape == (T, D, N) and codes.dtype == np.dtype("int" + str(bits)),
                "Mamba2 state storage format")
        lo, hi = -(1 << (bits - 1)), (1 << (bits - 1)) - 1
    for t in range(T):
        # Operation order is part of the numerical contract.
        proposal = a[t] * state + x[t, :, None] * (dt[t] * b[t, None, :])
        require(np.isfinite(proposal).all(), "Mamba2 proposal finite")
        if bits:
            rounded = np.rint(proposal / unit)
            sat = int(np.count_nonzero((rounded < lo) | (rounded > hi)))
            wanted = np.clip(rounded, lo, hi).astype(codes.dtype)
            require(np.array_equal(wanted, codes[t]), "Mamba2 stored code replay")
            require(sat == int(z[key + ".saturations"][t]), "Mamba2 saturation count")
            picks = {(0, 0), (D - 1, N - 1), np.unravel_index(np.argmax(proposal), proposal.shape),
                     np.unravel_index(np.argmin(proposal), proposal.shape)}
            for ix in picks:
                value, saturated = fixed_from_float(float(proposal[ix]), exponent, bits)
                require(value == int(codes[(t,) + ix]), "Mamba2 exact IEEE RNE spot")
                spot += 1
            state = wanted.astype(np.float64) * unit
            sat_total += sat
        else:
            state = proposal
        states.append(state.copy())
        # Scalar Python sums at the two edge outputs avoid accepting only one
        # BLAS implementation as an independent output witness.
        y = state @ c[t] + skip * x[t]
        for d in {0, D - 1}:
            sy = math.fsum(float(state[d, j]) * float(c[t, j]) for j in range(N)) + skip * float(x[t, d])
            require(math.isclose(sy, float(y[d]), rel_tol=1e-11, abs_tol=1e-9), "Mamba2 output sum witness")
        output.append(y)
    states, output = np.asarray(states), np.asarray(output)
    ref = "S" + str(bits) if bits else prefix + ".fp64"
    state_error = compare_float(states, z[ref + "_states"] if not bits else z[ref + ".states"],
                                "Mamba2 states", atol=2e-10, rtol=2e-12)
    output_error = compare_float(output, z[ref + "_output"] if not bits else z[ref + ".output"],
                                 "Mamba2 outputs", atol=1e-8, rtol=2e-11)
    return dict(steps=T, D=D, N=N, storage_bits=bits, saturation_cells=sat_total,
                exact_rounding_spots=spot, state_max_abs=state_error, output_max_abs=output_error,
                qualification="FP64 coefficient/update bridge; fixed integer state storage only")


def verify_descriptors(report, capture, config):
    total = int(report["input"]["evaluation_tokens"])
    expected = dict(kv_key=(1, 2, total, 128), kv_value=(1, 2, total, 128),
                    conv=(1, 4608, 4), ssm=(1, 32, 128, 256))
    checked = 0
    for name, shape in expected.items():
        require(capture["full.final." + name].shape == shape, "complete state owner/shape " + name)
        initial = capture["initial." + name]
        require(initial.shape == ((1, 2, 0, 128) if name.startswith("kv_") else shape)
                and np.count_nonzero(initial) == 0, "empty initial state " + name)
        for phase in ("cached.final", "chunk1.final", "chunk8.final", "chunk16.final"):
            require(capture[phase + "." + name].shape == shape, "final shape " + phase + name)
            # Report all native differences without treating a stated tolerance
            # or a failed native chunk as mathematical integer acceptance.
            require(np.isfinite(capture[phase + "." + name]).all(), "native final finite")
            checked += 1
    for chunk in (1, 8, 16):
        rows = report["chunk_continuity"][str(chunk)]["checkpoints"]
        require(len(rows) == math.ceil(total / chunk), "all chunk boundaries described")
        for i, row in enumerate(rows):
            stop = min((i + 1) * chunk, total)
            require(row["owner"] == "layer0.hybrid" and row["next_position"] == stop
                    and row["epoch"] == 0 and row["version"] == stop,
                    "chunk owner/position/epoch/version consistency")
            require(row.get("descriptor_is_analysis_metadata_not_native_epoch_enforcement") is True,
                    "descriptor qualification")
            require(row["kv_shape"] == [1, 2, stop, 128] and row["conv_shape"] == [1, 4608, 4]
                    and row["ssm_shape"] == [1, 32, 128, 256], "chunk complete state shapes")
            checked += 1
    return dict(descriptors_and_shapes=checked,
                qualification="analysis metadata consistency only; not native epoch enforcement or long-context acceptance")


def verify_projection(z, *, full=False):
    w = z["weight_code"]
    require(w.dtype == np.int8 and w.ndim == 2 and w.shape[0] == 16, "projection W8 outputs")
    require(np.all(np.abs(w.astype(np.int16)) <= 127), "projection symmetric W8")
    values = 0
    encoded = 0
    if full:
        raw = np.asarray(z["weight"], np.float64)
        ws = np.maximum(np.max(np.abs(raw), axis=1), 1e-30) / 127
        require(np.array_equal(ws, z["weight_scale"]), "projection weight scale source")
        require(np.array_equal(np.clip(np.rint(raw / ws[:, None]), -127, 127).astype(np.int8), w),
                "projection W8 source encoding")
        encoded += w.size
    for scheme in ("cal_static_tensor", "eval_dynamic_row"):
        a, acc = z[scheme + "_input_code"], z[scheme + "_accumulator"]
        require(a.dtype == np.int8 and acc.dtype == np.int32 and a.shape[1] == w.shape[1]
                and acc.shape == (a.shape[0], 16), "projection A8/accumulator shape")
        require(np.all(np.abs(a.astype(np.int16)) <= 127), "projection symmetric A8")
        if full:
            raw = np.asarray(z["evaluation_input"], np.float64)
            cal = np.asarray(z["calibration_input"], np.float64)
            # The producer receives FP32 captured norm*MuP inputs, then stores
            # them losslessly as FP64. Its dynamic max/divide and activation
            # divide remain FP32; static Python-float scale is FP64. Recreate
            # those explicit bridge dtypes, not a different FP64 quantizer.
            raw32,cal32=raw.astype(np.float32),cal.astype(np.float32)
            require(np.array_equal(raw32.astype(np.float64),raw)
                    and np.array_equal(cal32.astype(np.float64),cal),
                    "projection stored input must be exact FP32 cast")
            scales = (np.full((len(raw), 1), max(float(np.max(np.abs(cal32))), 1e-30) / 127)
                      if scheme == "cal_static_tensor" else
                      np.maximum(np.max(np.abs(raw32), axis=1, keepdims=True), 1e-30) / 127)
            require(np.array_equal(scales, z[scheme + "_input_scale"]), "projection A scale source")
            wanted = np.clip(np.rint(raw32 / scales), -127, 127).astype(np.int8)
            require(np.array_equal(a, wanted), "projection A8 source encoding")
            compare_float(z[scheme + "_dequant"], acc * scales * z["weight_scale"][None, :],
                          "projection FP dequant", atol=1e-12, rtol=1e-13)
            encoded += a.size
        for t, j in np.ndindex(acc.shape):
            total = sum(int(v) * int(q) for v, q in zip(a[t], w[j]))
            require(-(1 << 31) <= total < 1 << 31 and total == int(acc[t, j]),
                    "projection independent complete-K dot")
            require(127 * sum(abs(int(q)) for q in w[j]) < (1 << 31), "projection INT32 conditional bound")
            values += 1
    return dict(complete_dot_values=values, source_encoding_values=encoded, K=w.shape[1], outputs=16,
                activation_bridge="FP32 stored exactly as FP64; dynamic max/division FP32, static scale/division FP64",
                qualification="stored W8A8 codes; floating scale bridge remains")


def verify_coefficients(z, cap, cfg):
    """Source-derived FP64 conv/SiLU/softplus/exp bridge, never an INT claim."""
    inner, N = 4096, 256
    channels = inner + 2 * N
    weight = cap["weight.conv_weight"].astype(np.float64)
    require(weight.shape == (channels, 1, 4), "complete causal conv weight")
    bias = cap.get("weight.conv_bias", np.zeros(channels)).astype(np.float64)
    checked = 0
    for phase in ("calibration", "evaluation"):
        p = cap[phase + ".projected"].astype(np.float64)
        raw = p[:, inner:inner + channels]
        padded = np.pad(raw, ((3, 0), (0, 0)))
        conv = np.empty_like(raw)
        for t in range(len(raw)):
            pre = np.sum(padded[t:t+4].T * weight[:, 0], axis=1) + bias
            conv[t] = pre / (1 + np.exp(-pre))
        raw_dt = p[:, inner + channels]
        dt = np.logaddexp(0, raw_dt + float(cap["weight.dt_bias"][0]))
        limits = cfg.get("mamba_time_step_limit", cfg.get("time_step_limit", [0.0, float("inf")]))
        dt = np.clip(dt, float(limits[0]), float(limits[1]))
        alog = float(cap["weight.A_log"][0])
        expected = dict(x=conv[:, :128], b=conv[:, inner:inner+N],
                        c=conv[:, inner+N:inner+2*N], dt=dt,
                        a=np.exp(-np.exp(alog) * dt))
        for name, value in expected.items():
            compare_float(value, z[phase + "." + name], "source-derived FP64 coefficient " + phase + name,
                          atol=1e-11, rtol=2e-12)
            checked += value.size
    return dict(values=checked, qualification="floating coefficient bridge independently rebuilt; nonlinear/SFU implementation unqualified")


def float_gate(got, expected, rtol, atol):
    a, b = np.asarray(got, np.float64), np.asarray(expected, np.float64)
    require(a.shape == b.shape and np.isfinite(a).all() and np.isfinite(b).all(), "native gate shape/finite")
    diff = a - b
    maximum = float(np.max(np.abs(diff))) if diff.size else 0.0
    relative = float(np.linalg.norm(diff) / max(float(np.linalg.norm(b)), 1e-30))
    return dict(relative_l2=relative, max_abs=maximum, relative_limit=rtol, absolute_limit=atol,
                passed=relative <= rtol and maximum <= atol)


def native_falcon_gates(z, cap, joined):
    """Frozen pre-run criteria; failures remain data, never silently relaxed."""
    gates = {"cached_last_logits":float_gate(cap["cached.decode_logits"][:, -1:],
                                            cap["evaluation.last_logits"], 2e-4, 1e-2),
             "parallel_join":float_gate(joined,cap["evaluation.pre_ff_input"],2e-6,1e-3),
             "FP64_head_state":float_gate(z["evaluation.fp64_states"],z["native.head0.states"],2e-4,1e-3),
             "FP64_head_output":float_gate(z["evaluation.fp64_output"],z["native.head0.output"],2e-4,1e-3)}
    for chunk in (1,8,16):
        gates["chunk"+str(chunk)+"_output"] = float_gate(cap[f"chunk{chunk}.output"],
                                                        cap["evaluation.layer_output"],2e-4,1e-2)
        for name in ("kv_key","kv_value","conv","ssm"):
            gates[f"chunk{chunk}_{name}"] = float_gate(cap[f"chunk{chunk}.final.{name}"],
                                                        cap["full.final."+name],2e-4,1e-2)
    for name in ("kv_key","kv_value","conv","ssm"):
        gates["cached_"+name] = float_gate(cap["cached.final."+name],cap["full.final."+name],2e-4,1e-2)
    return dict(passed=all(x["passed"] for x in gates.values()), conditions=gates,
                qualification="FP32 native and FP64 reference acceptance only; no integer state/application quality acceptance")


def falcon(result):
    m, files = manifest(result)
    source_commit(m)
    require(m.get("schema") == "falcon-h1-bounded-v1", "Falcon known schema")
    report, cfg = (read_json(Path(result) / name) for name in ("report.json", "config.json"))
    revision = report.get("model_revision", "")
    require(re.fullmatch("[0-9a-f]{40}", revision) is not None, "Falcon fixed revision")
    require(cfg["model_type"] == "falcon_h1" and cfg["mamba_n_heads"] == 32
            and cfg["mamba_d_head"] == 128 and cfg["mamba_d_state"] == 256
            and cfg["mamba_n_groups"] == 1, "Falcon Mamba2 configuration")
    z, cap, projection = (load_npz(Path(result) / name)
                          for name in ("numeric.npz", "capture.npz", "projection.npz"))
    require(projection["weight_code"].shape[1] == cfg["hidden_size"] == 2560,
            "Falcon projection complete hidden K2560")
    require(set(cap["calibration.tokens"].ravel()).isdisjoint(set(cap["evaluation.tokens"].ravel())),
            "calibration/evaluation IDs separated")
    coeff = verify_coefficients(z, cap, cfg)
    rec = [recurrence(z, p) for p in ("calibration", "evaluation")]
    rec += [recurrence(z, "evaluation", bits=b) for b in (16, 32)]
    desc = verify_descriptors(report, cap, cfg)
    joined = (cap["evaluation.input"].astype(np.float32)
              + cap["evaluation.mamba"] * cfg["ssm_out_multiplier"]
              + cap["evaluation.attention"] * cfg["attention_out_multiplier"])
    join_error = float(np.max(np.abs(joined - cap["evaluation.pre_ff_input"])))
    gates = native_falcon_gates(z, cap, joined)
    inner = cfg.get("mamba_d_ssm") or int(cfg["mamba_expand"] * cfg["hidden_size"])
    require(inner == 4096, "Falcon complete gated norm width")
    gate = cap["evaluation.projected"][:, :inner].astype(np.float64)
    raw = cap["evaluation.raw_scan"].astype(np.float64)
    gamma = cap["weight.gated_norm_gamma"].astype(np.float64)
    sg = gate / (1 + np.exp(-gate))
    g = raw if cfg["mamba_norm_before_gate"] else raw * sg
    expected = g / np.sqrt(np.mean(g * g, axis=1, keepdims=True) + cfg["rms_norm_eps"])
    expected *= gamma
    if cfg["mamba_norm_before_gate"]:
        expected *= sg
    compare_float(expected, z["gated_norm.fp64_reference"], "whole4096 gated RMSNorm", atol=1e-10, rtol=1e-11)
    # Native differences are returned as diagnostics. They are not redefined
    # into a pass by changing tolerances after seeing model data.
    native = dict(state_max_abs=float(np.max(np.abs(z["evaluation.fp64_states"] - z["native.head0.states"]))),
                  output_max_abs=float(np.max(np.abs(z["evaluation.fp64_output"] - z["native.head0.output"]))))
    return dict(model="Falcon-H1-3B-Instruct", revision=revision, source_commit=source_commit(m),
                result_manifest_sha256=sha(Path(result)/"manifest.json"), artifacts_checked=len(files),
                coefficients=coeff, recurrence=rec, descriptors=desc, projection=verify_projection(projection, full=True),
                hybrid_join_max_abs=join_error, gated_norm_elements=inner, native_fp64_differences=native,
                native_acceptance=gates,
                qualification="Mamba2 FP64/update with fixed integer state storage; not GDN or all-integer recurrence; canonical descriptors are analysis metadata")


def rewrite_artifact_manifest(folder, name):
    path = Path(folder) / "manifest.json"
    m = read_json(path)
    entry = artifact(Path(folder) / name)
    if isinstance(m["artifacts"], list):
        found = [r for r in m["artifacts"] if r["path"] == name]
        require(len(found) == 1, "negative artifact must be indexed")
        found[0].update(entry)
    else:
        require(name in m["artifacts"], "negative artifact must be indexed")
        m["artifacts"][name].update(entry)
    # Replace rather than truncate: negative folders may hardlink read-only
    # originals for efficiency. Never modify a producer inode in place.
    temp = path.with_suffix(".rewrite.json")
    write_json(temp, m)
    temp.replace(path)


def negative_folder(source, out):
    require(not Path(out).exists(), "negative folder already exists")
    Path(out).mkdir(parents=True)
    m = read_json(Path(source) / "manifest.json")
    entries = m["artifacts"]
    names = [x["path"] for x in entries] if isinstance(entries, list) else list(entries)
    for name in ["manifest.json"] + names:
        src, dst = local_path(source, name), local_path(out, name)
        dst.parent.mkdir(parents=True, exist_ok=True)
        try:
            os.link(src, dst)
        except OSError:
            shutil.copy2(src, dst)


def replace_npz(folder, name, z):
    target = Path(folder) / name
    temp = target.with_suffix(".rewrite.npz")
    np.savez_compressed(temp, **z)
    temp.replace(target)
    rewrite_artifact_manifest(folder, name)


def negatives(model, result, capture, out):
    """Real edited artifacts with fresh SHA, rejected by math/semantic checks."""
    records = []
    original_sha = sha(Path(result) / "manifest.json")
    for label in ("code", "route" if model == "granite" else "epoch"):
        dest = Path(out) / label
        negative_folder(result, dest)
        if model == "granite":
            z = load_npz(dest / "witnesses.npz")
            if label == "code":
                z["acc_0"] = z["acc_0"] + np.int64(1)
            else:
                key = "route_ids_q_dynamic_row"
                z[key] = z[key].copy()
                z[key][0, 0] = (int(z[key][0, 0]) + 1) % 40
            replace_npz(dest, "witnesses.npz", z)
        elif label == "code":
            z = load_npz(dest / "numeric.npz")
            z["S32.codes"] = z["S32.codes"].copy()
            v = int(z["S32.codes"][0, 0, 0])
            z["S32.codes"][0, 0, 0] = v - 1 if v == (1 << 31) - 1 else v + 1
            replace_npz(dest, "numeric.npz", z)
        else:
            report = read_json(dest / "report.json")
            report["chunk_continuity"]["8"]["checkpoints"][0]["epoch"] += 1
            temp = dest / "report.rewrite.json"
            write_json(temp, report)
            temp.replace(dest / "report.json")
            rewrite_artifact_manifest(dest, "report.json")
        # Demonstrate that these are semantic failures, not stale-SHA failures.
        manifest(dest)
        try:
            granite(dest, capture) if model == "granite" else falcon(dest)
        except ValueError as e:
            require("artifact SHA/size" not in str(e), "negative must pass hashes")
            records.append(dict(label=label, status="REJECTED", reason=str(e),
                                manifest_sha256=sha(dest / "manifest.json")))
        else:
            raise ValueError("actual rehashed negative was accepted: " + label)
    require(sha(Path(result) / "manifest.json") == original_sha, "producer manifest was mutated")
    manifest(result)
    return records


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--model", choices=("granite", "falcon"), required=True)
    p.add_argument("--result", type=Path, required=True)
    p.add_argument("--capture", type=Path)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--binding", type=Path)
    p.add_argument("--producer-source", type=Path,
                   help="frozen producer source file to verify the manifest source hash")
    p.add_argument("--skip-negatives", action="store_true",
                   help="explicit partial receipt only; standard acceptance includes edited artifacts")
    a = p.parse_args()
    require(not a.out.exists(), "refuse audit output overwrite")
    require(a.model != "granite" or a.capture is not None, "Granite capture required")
    a.out.mkdir(parents=True)
    receipt = dict(schema="issue70-independent-receiver-v1", status="FAIL", model=a.model,
                   receiver_sha256=sha(__file__), qualification="bounded mathematical/source reception, not application quality or target hardware acceptance")
    try:
        if a.binding:
            b = read_json(a.binding)
            require(re.fullmatch("[0-9a-f]{40}", b.get("commit", "")) is not None, "receiver commit binding")
            expected = b.get("receive_sha256", b.get("sources", {}).get("receive.py"))
            require(expected == sha(__file__), "receiver source hash binding")
            receipt["source"] = b
        pm = read_json(a.result / "manifest.json")
        producer_sha = pm.get("producer_sha256") if a.model == "falcon" else pm.get("source", {}).get("granite_sha256")
        require(re.fullmatch("[0-9a-f]{64}", producer_sha or "") is not None, "producer source SHA receipt")
        if a.producer_source:
            require(sha(a.producer_source) == producer_sha, "frozen producer source SHA mismatch")
            receipt["producer_source_checked"] = str(a.producer_source)
        else:
            receipt["producer_source_checked"] = "NOT_EXECUTED; manifest SHA syntax only, source capsule must be checked externally"
        receipt["checks"] = granite(a.result, a.capture) if a.model == "granite" else falcon(a.result)
        if a.skip_negatives:
            receipt["status"] = "PARTIAL"
            receipt["negatives"] = "NOT_EXECUTED"
        else:
            receipt["negatives"] = negatives(a.model, a.result, a.capture, a.out / "negatives")
            receipt["status"] = "PASS"
    except Exception as e:
        receipt["error"] = type(e).__name__ + ": " + str(e)
        write_json(a.out / "audit.json", receipt)
        raise
    write_json(a.out / "audit.json", receipt)
    print(json.dumps({"status": receipt["status"], "audit_sha256": sha(a.out / "audit.json")}))


if __name__ == "__main__":
    main()
