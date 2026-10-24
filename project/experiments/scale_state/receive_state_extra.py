"""Independent Issue66 extension: coupled conv32 and three predeclared legacy256 diagnostics.

Imports only the separately frozen independent receiver. All legacy scientific
artifacts are SHA/size checked in both rounds, but only SELECTED_LEGACY receives
a complete Python-int oracle. All floating bridges remain explicit.
"""
import argparse
from collections import Counter
from decimal import Decimal, localcontext, ROUND_HALF_EVEN
from fractions import Fraction
import math
from pathlib import Path
import re
import time

import numpy as np
import receive_state as b

DEPENDENCY_SHA = "4a08cd4c4242c4a37ba000c21ed06f2ebf44b60c476df163ff28d5d664c83a86"
SELECTED_LEGACY = ("layer14-end8192.S16.D15", "layer14-end8192.S32.D31",
                   "layer0-end8192.S32.D31")
STAGES = "decay RNE at declared fraction; prediction/beta/outer/output RNE15; state-only final saturation"


def require(condition, label):
    if not condition:
        raise AssertionError(label)


def same(actual, wanted, label):
    require(np.array_equal(actual, wanted), label)


def repeated(first, second):
    m1, r1 = b.manifest(first)
    m2, r2 = b.manifest(second)
    require(r1 == r2, "two-round complete scientific artifact SHA/bytes")
    # Source binding must also agree; timing/job metadata can differ.
    require(m1.get("source", m1.get("source_commit")) == m2.get("source", m2.get("source_commit")),
            "two-round source provenance")
    return m1, r1, dict(all_scientific_artifacts_identical=True, artifacts=len(r1),
                        bytes=sum(d["bytes"] for d in r1.values()),
                        arithmetic_rounds=1, repeat_scope="all SHA/bytes, not a second arithmetic execution")


def load_npz(path):
    with np.load(path, allow_pickle=False) as z:
        return {k: z[k] for k in z.files}


def fraction_encode(values, exponents, low, high):
    x = np.asarray(values)
    exponents = np.broadcast_to(np.asarray(exponents), x.shape)
    codes = np.empty(x.shape, np.int64)
    clips = 0
    for ix in np.ndindex(x.shape):
        n = round(Fraction.from_float(float(x[ix])) * Fraction(2) ** -int(exponents[ix]))
        clips += n < low or n > high
        codes[ix] = max(low, min(high, n))
    return codes, clips


def cover(values, bound, headroom=1, floor=None, zero=0):
    maximum = max(abs(Fraction.from_float(float(v))) for v in np.asarray(values).ravel())
    if not maximum:
        return zero
    maximum *= headroom
    e = floor if floor is not None else 0
    if floor is None:
        while Fraction(bound) * Fraction(2) ** (e - 1) >= maximum:
            e -= 1
    while Fraction(bound) * Fraction(2) ** e < maximum:
        e += 1
    return e


def normalized(payload):
    q = np.asarray(payload["query"], np.float64)[0].copy()
    k = np.asarray(payload["key"], np.float64)[0].copy()
    require(q.shape == k.shape and q.shape[1:] == (2, 128), "normalization shape")
    for x, scale in ((q, math.sqrt(128)), (k, 1)):
        for t in range(len(x)):
            for h in range(2):
                inv = 1 / math.sqrt(math.fsum(float(v) ** 2 for v in x[t, h]) + 1e-6)
                x[t, h] *= inv / scale
    return dict(q=q, k=k, v=np.asarray(payload["value"], np.float64)[0],
                beta=np.asarray(payload["beta"], np.float64)[0],
                g=np.asarray(payload["g"], np.float64)[0])


def floating(payload):
    source = normalized(payload)
    state = np.asarray(payload["initial_state"], np.float64)[0].copy()
    states, ys = [state.copy()], []
    for t in range(len(source["q"])):
        state = state * np.exp(source["g"][t])[:, None, None]
        prediction = np.sum(state * source["k"][t, :, :, None], axis=1)
        delta = (source["v"][t] - prediction) * source["beta"][t, :, None]
        state += source["k"][t, :, :, None] * delta[:, None, :]
        ys.append(np.sum(state * source["q"][t, :, :, None], axis=1))
        states.append(state.copy())
    return np.stack(ys), np.stack(states), source


def encode_source(source, eV, fraction):
    codes, clips = {}, {}
    for field in ("q", "k"):
        codes[field], clips[field] = fraction_encode(source[field], -15, -32767, 32767)
    codes["v"], clips["v"] = fraction_encode(source["v"], np.asarray(eV)[None, :, None], -32767, 32767)
    codes["beta"], clips["beta"] = fraction_encode(source["beta"], -15, 0, 32768)
    decay = np.empty(source["g"].shape, np.int64)
    with localcontext() as ctx:
        ctx.prec = 60
        for ix in np.ndindex(decay.shape):
            d = Decimal.from_float(float(source["g"][ix])).exp() * Decimal(1 << fraction)
            decay[ix] = max(0, min(1 << fraction, int(d.to_integral_value(rounding=ROUND_HALF_EVEN))))
    codes["decay"], clips["decay"] = decay, 0
    return codes, clips


def continuous_oracle(arrays, eV, eS, lo, hi, fraction):
    """Eight legacy chunks carry computed state; no reset from saved snapshots."""
    T = len(arrays["q"])
    require(T in (32, 256), "frozen32/256 step scope")
    current = arrays["state_initial"].astype(np.int64)
    outputs, states = [], [current.copy()]
    counts, maxima, widths = Counter(), Counter(), Counter()
    for start in range(0, T, 32):
        stop = start + 32
        y, s, c, m, w = b.integer_oracle(
            *(arrays[name][start:stop] for name in ("q", "k", "v", "beta", "decay")),
            current, eV, eS, lo, hi,
            wanted_output=arrays["output_codes"][start:stop],
            wanted_states=arrays["state_trace"][start:stop + 1], decay_fraction=fraction)
        same(s[0], current, "computed chunk handoff state")
        current = s[-1].copy()
        outputs.append(y)
        states.extend(s[1:])
        counts.update(c)
        for key, value in m.items():
            maxima[key] = max(maxima[key], value)
        for key, value in w.items():
            widths[key] = max(widths[key], value)
    return np.concatenate(outputs), np.stack(states), dict(counts), dict(maxima), dict(widths)


def commits(row, states, outputs, source_manifest_sha, start, legacy):
    fmt = row["format"]
    sequence = "unknown:" + fmt["window"] + ": no cross-window commits" if legacy else b.json_digest(
        dict(source=source_manifest_sha, window=fmt["window"]))
    require(fmt["sequence"] == sequence, "sequence descriptor/cross-window scope")
    require(fmt["head_slots"] == [0, 1] and fmt["format_epoch"] == 0, "head/epoch descriptor")
    contract = b.json_digest(fmt)
    T = len(outputs)
    require(len(row["execution"]["commits"]) == T, "commit count")
    for t, event in enumerate(row["execution"]["commits"]):
        wanted = dict(version=t + 1, position=start + t + 1, contract=contract,
                      old_state_sha256=b.semantic_digest(states[t]),
                      state_sha256=b.semantic_digest(states[t + 1]),
                      output_sha256=b.semantic_digest(outputs[t]))
        require(event == wanted, "integer commit continuity " + str(t))
    require(row["execution"]["final_version"] == T and
            row["execution"]["final_position"] == start + T, "final position/version")


def diagnostic_metrics(row, y, states, eS, payload, fy, fs, coupled=None):
    physical_y = np.ldexp(y.astype(np.float64), np.asarray(eS)[None, :, None])
    physical_s = np.ldexp(states.astype(np.float64), np.asarray(eS)[None, :, None, None])
    native_y = np.asarray(payload["output"])[0]
    observed = []
    for sample in row["error_by_length"]:
        n = sample["steps"]
        require(n in (1, 8, 32, len(y)), "frozen diagnostic sample")
        wanted = dict(output_vs_native=b.metric(physical_y[:n], native_y[:n]),
                      state_vs_FP64_replay=b.metric(physical_s[n], fs[n]))
        if "state_boundaries" in payload:
            wanted["state_vs_native_capture"] = b.metric(physical_s[n], payload["state_boundaries"][n, 0])
        if n == len(native_y) and ("state_boundaries" not in payload or "state_vs_native_final" in sample):
            wanted["state_vs_native_final"] = b.metric(physical_s[n], payload["final_state"][0])
        if coupled is not None:
            cy, cs = coupled
            wanted.update(output_vs_FP64_same_coupled_input=b.metric(physical_y[:n], cy[:n]),
                          state_vs_FP64_same_coupled_input=b.metric(physical_s[n], cs[n]),
                          FP64_coupled_output_vs_native=b.metric(cy[:n], native_y[:n]))
        for field, value in wanted.items():
            require(field in sample, "missing diagnostic " + field)
            for stat, number in value.items():
                require(math.isclose(number, sample[field][stat], rel_tol=1e-8, abs_tol=1e-10),
                        "independent metric " + row["id"] + " " + field)
        observed.append(dict(steps=n, **wanted))
    require({s["steps"] for s in observed} == {1, 8, 32, len(y)}, "missing length diagnostic")
    return observed


def verify_record(folder, row, payload, eS, eV, source_manifest_sha, source_npz_sha,
                  start, legacy=False, coupled_payload=None):
    bits, fraction = row["format"]["state_bits"], row["format"]["decay_fraction"]
    T = len(payload["output"][0])
    require(row["status"] == "PASS_INTEGER_EXECUTION" and row["integer_steps"] == T and
            row["original_native_steps"] == T, "complete actual window execution")
    fmt = row["format"]
    require(fmt["state_unit"] == list(map(int, eS)) and fmt["value_unit"] == list(map(int, eV)),
            "fixed source scale compiler")
    require(fmt["QK_unit"] == -15 and fmt["beta_unit"] == -15 and fmt["stage_contract"] == STAGES,
            "declared stage formats/RNE/saturation")
    require(fmt["source_input_sha256"] == source_npz_sha, "source NPZ descriptor")
    require(row["quality_accepted"] is False and row["hardware_implemented"] is False,
            "software execution must not assert full-model or hardware acceptance")
    a = load_npz(Path(folder) / row["artifact"]["name"])
    state_dtype = np.dtype("int16" if bits == 16 else "int32")
    require(a["state_initial"].shape == (2, 128, 128) and
            a["state_trace"].shape == (T + 1, 2, 128, 128) and
            a["output_codes"].shape == (T, 2, 128), "complete typed trajectory shapes")
    require(a["state_initial"].dtype == state_dtype and a["state_trace"].dtype == state_dtype and
            a["output_codes"].dtype == np.dtype("int64"), "declared integer state/output containers")
    require(all(a[field].dtype == np.dtype("int16") for field in ("q", "k", "v")) and
            a["beta"].dtype == np.dtype("uint16") and
            a["decay"].dtype == np.dtype("uint16" if fraction == 15 else "uint32"),
            "unsigned gate endpoint and signed QKV containers")
    same(a["state_units"], eS, "NPZ state units")
    same(a["value_units"], eV, "NPZ V units")
    fy, fs, source = floating(payload)
    require(b.metric(fy, payload["output"][0])["relative_rmse"] < 1e-4 and
            b.metric(fs[-1], payload["final_state"][0])["relative_rmse"] < 1e-4,
            "complete native window FP64 recurrence reference")
    b.close(fy, payload["output"][0], "actual FP64/native window output")
    b.close(fs[-1], payload["final_state"][0], "actual FP64/native final state")
    b.close(a["FP64_state_reference"], fs, "saved native-input FP64 state", atol=1e-10, rtol=1e-10)
    same(a["native_output"], payload["output"][0], "native output identity")
    if "state_boundaries" in payload:
        same(a["native_state_reference"], payload["state_boundaries"][:, 0], "actual native state identity")
    couple = None
    if coupled_payload is not None:
        cy, cs, source = floating(coupled_payload)
        b.close(a["FP64_coupled_input_output_reference"], cy, "saved same-coupled output", atol=1e-10, rtol=1e-10)
        b.close(a["FP64_coupled_input_state_reference"], cs, "saved same-coupled state", atol=1e-10, rtol=1e-10)
        couple = cy, cs
    encoded, clips = encode_source(source, eV, fraction)
    for field in encoded:
        same(a[field], encoded[field], "independent source bridge " + field)
    require(clips == row["operand_bridge_clips"], "operand bridge clip statistics")
    lo, hi = (-32768, 32767) if bits == 16 else (-(1 << 31), 32767 << 16)
    initial, initial_clips = fraction_encode(payload["initial_state"][0], np.asarray(eS)[:, None, None], lo, hi)
    same(a["state_initial"], initial, "initial state encoded once")
    require(initial_clips == row["initial_bridge_code_clips"], "initial clip count")
    y, states, counts, maxima, widths = continuous_oracle(a, eV, eS, lo, hi, fraction)
    require(row["execution"]["saturations"] == counts["state_saturations"], "independent saturation count")
    require(row["execution"]["observed_absolute_max"] == maxima, "observed intermediate maxima")
    commits(row, states, y, source_manifest_sha, start, legacy)
    # Every coded decay equal to1 is counted against actual g<0, not an artificial epsilon.
    exact_one = int(np.count_nonzero((source["g"] < 0) & (encoded["decay"] == (1 << fraction))))
    require(row["decay_near_one"]["integer_prefix_source_less_than1_encoded_exact1"] == exact_one,
            "near1 decay diagnostic")
    metrics = diagnostic_metrics(row, y, states, eS, payload, fy, fs, couple)
    return dict(id=row["id"], status="PASS_INDEPENDENT_ARITHMETIC", steps=T,
                chunks=T // 32, computed_state_carried_between_chunks=True,
                counts=counts, required_signed_bits=widths,
                source_clips=clips, initial_clips=initial_clips, decay_rounded_exact1=exact_one,
                error_by_length=metrics, state_values=int(states.size), output_values=int(y.size),
                quality_accepted=False, hardware_implemented=False)


def coupled_conv_source(conv, conv_repeat, capture, raw):
    cm, checked, repeat = repeated(conv, conv_repeat)
    require(cm["capture_manifest_sha256"] == b.sha(Path(capture) / "manifest.json") and
            cm["input_sha256"] == b.sha(Path(capture) / "state-raw.npz"), "conv raw source binding")
    z = load_npz(Path(conv) / "conv-output.npz")
    w = raw["weight.conv"]
    ew = np.array([cover(row, 127) for row in w], np.int64)
    wc, wcclips = fraction_encode(w, ew[:, None], -127, 127)
    same(z["weight.codes"], wc, "conv Fraction W8 source")
    same(z["weight.exponent"], ew, "conv fixed W exponents")
    payloads, counts = {}, []
    for bits in (8, 16):
        limit = (1 << (bits - 1)) - 1
        cal = np.concatenate([raw["calibration.conv.boundaries"][0], raw["calibration.conv.input"]], axis=-1)
        ea = np.array([cover(cal[:, c], limit) for c in range(512)], np.int64)
        same(z["conv%d.activation_exponent" % bits], ea, "conv calibration-only activation scale")
        tag = "conv%d.evaluation." % bits
        x, input_clips = fraction_encode(raw["evaluation.conv.input"], ea[None, :, None], -limit, limit)
        history, history_clips = fraction_encode(raw["evaluation.conv.boundaries"][0], ea[None, :, None], -limit, limit)
        same(z[tag + "input.codes"], x, "conv actual source codes")
        same(z[tag + "initial.codes"], history, "conv actual initial history codes")
        same(z[tag + "history.codes"][0], history, "conv encoded history boundary0")
        observed = np.empty((1, 512, 32), np.float64)
        for t in range(32):
            history = np.concatenate([history[..., 1:], x[..., t:t + 1]], axis=-1)
            same(z[tag + "history.codes"][t + 1], history, "conv continuous encoded history")
            dots = np.array([[sum(int(history[0, c, j]) * int(wc[c, j]) for j in range(4))
                              for c in range(512)]], np.int64)
            require(np.max(np.abs(dots)) <= (1 << 31) - 1, "conv full fourtap accumulator overflow")
            same(z[tag + "accumulator"][..., t], dots, "conv independent Pythonint fourtap dot")
            physical = np.ldexp(dots.astype(np.float64), (ea + ew)[None, :])
            for c in range(512):
                u = float(physical[0, c])
                sig = 1 / (1 + math.exp(-u)) if u >= 0 else math.exp(u) / (1 + math.exp(u))
                observed[0, c, t] = u * sig
        b.close(z[tag + "post_silu_fp64"], observed, "conv explicit FP64 SiLU bridge", atol=1e-14, rtol=1e-14)
        q = np.repeat(observed[:, :128].transpose(0, 2, 1)[:, :, None], 2, axis=2)
        k = np.repeat(observed[:, 128:256].transpose(0, 2, 1)[:, :, None], 2, axis=2)
        v = observed[:, 256:].reshape(1, 2, 128, 32).transpose(0, 3, 1, 2)
        payloads["conv%d" % bits] = dict(query=q, key=k, value=v)
        for field, value in payloads["conv%d" % bits].items():
            b.close(z[tag + field], value, "conv shared-key QKV layout", atol=1e-14, rtol=1e-14)
        metrics = b.read_json(Path(conv) / "metrics.json")
        row = next(r for r in metrics if r["profile"] == "conv%d" % bits and r["case"] == "evaluation")
        require((input_clips, history_clips, wcclips) ==
                (row["source_input_clips"], row["initial_history_clips"], row["weight_clips"]),
                "conv retained source clipping failures")
        counts.append(dict(profile="conv%d" % bits, input_clips=input_clips, initial_history_clips=history_clips,
                           fourtap_integer_dots=32 * 512, source_calibration_fixed=True))
    return payloads, dict(source_manifest_sha256=b.sha(Path(conv) / "manifest.json"),
                          source_NPZ_sha256=b.sha(Path(conv) / "conv-output.npz"),
                          artifacts=checked, repeat=repeat, evaluation=counts,
                          integer_SiLU_accepted=False)


def verify_coupled(folder, capture, raw, conv, payloads, limit=None):
    meta, receipts = b.manifest(folder)
    source = meta["source"]
    capture_sha, input_sha = b.sha(Path(capture) / "manifest.json"), b.sha(Path(capture) / "state-raw.npz")
    require(source["input_manifest_sha256"] == capture_sha and source["input_NPZ_sha256"] == input_sha and
            source["input_NPZ_name"] == "state-raw.npz",
            "coupled source/capture binding")
    require(source["conv_input"] == dict(manifest_sha256=b.sha(Path(conv) / "manifest.json"),
                                        NPZ_sha256=b.sha(Path(conv) / "conv-output.npz"),
                                        capture_manifest_sha256=capture_sha), "coupled exact integer-conv binding")
    rows = b.read_json(Path(folder) / "state-results.json")
    wanted = {"evaluation.conv8.S32.D31", "evaluation.conv16.S32.D31"}
    require(len(rows) == 2 and {r["id"] for r in rows} == wanted and meta["integer_conditions"] == 2,
            "frozen coupled two-profile matrix")
    e16, eV = b.calibration_units(raw)
    eS = e16.astype(np.int64) - 16
    fields = ("query", "key", "value", "g", "beta", "initial_state", "output", "final_state", "state_boundaries")
    native = {name: raw["evaluation." + name] for name in fields}
    result = []
    for row in rows[:limit] if limit else rows:
        variant = row["format"]["input_variant"]
        require(row["format"]["window"] == "evaluation" and row["format"]["state_bits"] == 32 and
                row["format"]["decay_fraction"] == 31 and variant in ("conv8", "conv16"), "coupled profile contract")
        art = row["artifact"]
        require(receipts[art["name"]] == dict(bytes=art["bytes"], sha256=art["sha256"]), "coupled row artifact")
        cp = dict(native)
        cp.update(payloads[variant])
        result.append(verify_record(folder, row, native, eS, eV, capture_sha, input_sha, 128,
                                    coupled_payload=cp))
    return result


def verify_legacy(folder, legacy, selected=SELECTED_LEGACY):
    lm, raw_checked = b.manifest(legacy)
    require(set(lm["windows"]) == {"layer%d-end%d" % (layer, end) for layer in (0, 14, 30)
                                    for end in (2048, 2049, 8192, 8193)}, "actual legacy12 windows")
    require(not lm.get("calibration_windows"), "legacy diagnostics must not invent calibration holdout")
    meta, checked = b.manifest(folder)
    manifest_sha, npz_sha = b.sha(Path(legacy) / "manifest.json"), b.sha(Path(legacy) / "windows.npz")
    require(meta["source"]["input_manifest_sha256"] == manifest_sha and
            meta["source"]["input_NPZ_sha256"] == npz_sha and
            meta["source"]["input_NPZ_name"] == "windows.npz", "legacy lossless source binding")
    rows = b.read_json(Path(folder) / "state-results.json")
    require(len(rows) == 48 and meta["integer_conditions"] == 48, "all48 legacy execution metadata")
    expected = {name + ".S%d.D%d" % (bits, df) for name in lm["windows"] for bits in (16, 32) for df in (15, 31)}
    require({r["id"] for r in rows} == expected, "legacy profile set")
    result = []
    with np.load(Path(legacy) / "windows.npz", allow_pickle=False) as z:
        for ident in selected:
            row = next(r for r in rows if r["id"] == ident)
            name = row["format"]["window"]
            fields = ("query", "key", "value", "g", "beta", "initial_state", "output", "final_state")
            p = {field: z[name + "." + field] for field in fields}
            require(p["query"].shape == (1, 256, 2, 128) and p["initial_state"].shape == (1, 2, 128, 128),
                    "actual contiguous legacy256 shape")
            units16 = np.array([cover(p["initial_state"][0, h], 32767, headroom=2, floor=-26, zero=-20)
                                for h in range(2)], np.int64)
            bits = row["format"]["state_bits"]
            eS, eV = units16 - (16 if bits == 32 else 0), np.array([-10, -10])
            art = row["artifact"]
            require(checked[art["name"]] == dict(bytes=art["bytes"], sha256=art["sha256"]), "legacy row artifact")
            require(row["role"] == "previously observed legacy diagnostic" and
                    row["format"]["input_variant"] == "native", "legacy scope/variant")
            start = int(re.fullmatch(r"layer\d+-end(\d+)", name).group(1)) - 256
            result.append(verify_record(folder, row, p, eS, eV, manifest_sha, npz_sha, start, legacy=True))
    return result, dict(artifacts=raw_checked, manifest_sha256=manifest_sha,
                        oracle_ids=list(selected), oracle_profiles=len(selected), total_profiles=48,
                        selection_reason="predeclared near1/extreme formats plus explicitly reported saturation failure witness; diagnostic, not holdout")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for arg in ("capture", "conv", "conv-repeat", "coupled", "coupled-repeat", "legacy", "long", "long-repeat", "out"):
        parser.add_argument("--" + arg, type=Path, required=True)
    parser.add_argument("--binding", type=Path)
    parser.add_argument("--no-negatives", action="store_true")
    args = parser.parse_args()
    require(not args.out.exists(), "new output directory")
    require(b.sha(Path(b.__file__)) == DEPENDENCY_SHA, "frozen independent receiver dependency SHA")
    binding = None
    if args.binding:
        binding = b.read_json(args.binding)
        require(binding["receive_state_extra_sha256"] == b.sha(__file__) and
                binding["receive_state_sha256"] == DEPENDENCY_SHA and len(binding["commit"]) == 40,
                "extension source/dependency/commit binding")
    begin = time.monotonic()
    raw, raw_receipt = b.raw_capture(args.capture)
    payloads, conv = coupled_conv_source(args.conv, args.conv_repeat, args.capture, raw)
    _, _, coupled_repeat = repeated(args.coupled, args.coupled_repeat)
    _, _, long_repeat = repeated(args.long, args.long_repeat)
    coupled = verify_coupled(args.coupled, args.capture, raw, args.conv, payloads)
    legacy, legacy_source = verify_legacy(args.long, args.legacy)
    args.out.mkdir(parents=True)
    negatives = []
    if not args.no_negatives:
        for label, code in (("rehashed-coupled-output", True), ("rehashed-coupled-commit", False)):
            destination = args.out / label
            b.rehashed_negative_integer(args.coupled, destination, code)
            b.manifest(destination)  # Actual altered artifact with rewritten SHA passes the index first.
            try:
                verify_coupled(destination, args.capture, raw, args.conv, payloads, limit=1)
            except AssertionError as error:
                expected = "integer output oracle" if code else "integer commit continuity"
                require(expected in str(error), "negative wrong rejection reason " + str(error))
                negatives.append(dict(name=label, rewritten_SHA_passed=True,
                                      semantic_rejected=True, error=str(error)))
            else:
                raise AssertionError("coupled corruption accepted")
    counts = Counter()
    for record in coupled + legacy:
        counts.update(record["counts"])
    result = dict(status="PASS_INDEPENDENT_ARITHMETIC", receiver_sha256=b.sha(__file__),
                  dependency_sha256=DEPENDENCY_SHA, source_binding=binding,
                  raw_capture=raw_receipt, conv=conv, coupled=coupled, legacy=legacy,
                  legacy_source=legacy_source, repeat=dict(coupled=coupled_repeat, legacy=long_repeat),
                  counts=dict(counts), negatives=negatives, seconds=time.monotonic() - begin,
                  full48_legacy_oracle_executed=False, integer_nonlinear_hardware_accepted=False,
                  full_model_quality_accepted=False, target_hardware_accepted=False,
                  scope="Only2 coupled32 and3 actual legacy256 profiles get full integer oracle; all48 long and all2 coupled artifacts get repeat SHA/bytes checks. RNE and chunks are exact; conv SiLU, QK L2norm, gate/exp/source compilers stay explicit floating bridges. Retained clipping/saturation are quality failures, not receiver arithmetic failures.")
    b.save_json(args.out / "audit-extra.json", result)
    print({"status": result["status"], "coupled": len(coupled), "legacy_oracle": len(legacy), "counts": dict(counts)})


if __name__ == "__main__":
    main()
