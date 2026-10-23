"""Local-only controlled numerical experiment on an existing, hash-pinned real head."""
import argparse
from collections import Counter
from fractions import Fraction
import hashlib
import io
import json
import math
from pathlib import Path
import platform
import subprocess
import sys
import zipfile

import numpy as np
from core import integer_attention, requant_wide, checked
from oracle import attention as oracle_attention, dyadic
from quantize import compile_ratio, error
from tables import load

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def save(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
                    encoding="utf-8", newline="\n")


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT).decode().strip()


def source_record(development):
    paths = sorted([*HERE.glob("*.py"), HERE / "experiment.json",
        *[(HERE.parent / "integer_precision" / n) for n in
          ("fixed.py", "vectors.py", "tables.py", "tables.json", "quantize.py")]])
    commit = git("rev-parse", "HEAD")
    bindings = {}
    for path in paths:
        relative = path.relative_to(ROOT).as_posix()
        raw = path.read_bytes()
        tracked = subprocess.run(["git", "show", f"{commit}:{relative}"], cwd=ROOT,
                                 capture_output=True)
        bindings[relative] = {"sha256": sha(raw), "in_commit": tracked.returncode == 0,
                             "matches_commit": tracked.returncode == 0 and raw == tracked.stdout}
    dirty = bool(git("status", "--porcelain"))
    if not development and (dirty or not all(b["matches_commit"] for b in bindings.values())):
        raise ValueError("formal run requires clean, commit-bound source")
    return {"commit": commit, "dirty": dirty, "development": development, "files": bindings,
            "python": platform.python_version(), "numpy": np.__version__,
            "host": "Liangruizhi local PC", "backend": "CPU Python integer reference, not accelerator timing"}


def quantize(x):
    """Exploratory offline scales, using each block's full observed values (not quality calibration)."""
    maximum = float(np.max(np.abs(x)))
    exponent = max(-120, math.ceil(math.log2(maximum / 127))) if maximum else -24
    checked(exponent, 8)
    scaled = x.astype(np.float64) / 2.0 ** exponent
    rounded = np.rint(scaled)
    clipped = int(np.count_nonzero((rounded < -127) | (rounded > 127)))
    return np.clip(rounded, -127, 127).astype(np.int8), exponent, clipped


def softmax(scores, allowed):
    masked = np.where(allowed, scores, -np.inf)
    exp = np.exp(masked - np.max(masked, axis=1, keepdims=True))
    return exp / np.sum(exp, axis=1, keepdims=True)


def evaluate(name, sample, block, pbits, profile, table):
    q, k, v = (sample[n].astype(np.float64) for n in ("query", "key", "value"))
    original_q, original_k = q.copy(), k.copy()
    balance = np.zeros(q.shape[1], dtype=np.int8)
    if profile == "offline_dyadic_QK_balance":
        qmax = np.maximum(np.max(abs(q), axis=0), 1e-30)
        kmax = np.maximum(np.max(abs(k), axis=0), 1e-30)
        balance = np.clip(np.rint(0.5*np.log2(kmax/qmax)), -8, 8).astype(np.int8)
        q = q * np.exp2(balance.astype(np.float64))[None, :]
        k = k * np.exp2(-balance.astype(np.float64))[None, :]
        if not np.allclose(q @ k.T, original_q @ original_k.T, atol=1e-10, rtol=1e-12):
            raise AssertionError("dyadic QK transform changed real dot product")
    elif profile != "direct":
        raise ValueError("unknown input profile")
    positions = sample["query_positions"]
    allowed = np.arange(len(k))[None, :] <= positions[:, None]
    if bool(sample["mask_present"]):
        if not np.array_equal(sample["additive_mask"] == 0, allowed):
            raise ValueError("actual capture mask mismatch")
    elif len(q) != 1 or not allowed.all():
        raise ValueError("unexpected absent mask")
    qs, qe, ks, ke, vs, ve = [], [], [], [], [], []
    clipped = 0
    for query in q:
        a, e, c = quantize(query); qs.append(a); qe.append(e); clipped += c
    for start in range(0, len(k), block):
        a, e, c = quantize(k[start:start + block]); ks.extend(a); ke.append(e); clipped += c
        a, e, c = quantize(v[start:start + block]); vs.extend(a); ve.append(e); clipped += c
    qi, ki, vi = (np.asarray(a, dtype=np.int8) for a in (qs, ks, vs))
    # Float-only scale compiler is an explicit capability gap, not runtime integer hardware.
    params = [[compile_ratio(2.0 ** (eq + ek) / math.sqrt(q.shape[1]) * 256)
               for ek in ke] for eq in qe]
    rows, counts = integer_attention(qi.tolist(), ki.tolist(), vi.tolist(), ke, ve,
        params, block, pbits, allowed.tolist(), table)
    oracle = oracle_attention(qi.tolist(), ki.tolist(), vi.tolist(), ve,
        params, block, pbits, allowed.tolist(), table)
    comparisons = 0
    for left, right in zip(rows, oracle):
        for field, expected in right.items():
            if left[field] != expected:
                raise AssertionError(f"independent integer mismatch: {name}/{field}")
            comparisons += len(expected)
    qdq = qi.astype(np.float64) * np.exp2(qe)[:, None]
    kdq = ki.astype(np.float64) * np.exp2(np.repeat(ke, block)[:len(k)])[:, None]
    vdq = vi.astype(np.float64) * np.exp2(np.repeat(ve, block)[:len(v)])[:, None]
    original_scores = q @ k.T / math.sqrt(q.shape[1])
    fp = softmax(original_scores, allowed) @ v
    if not np.allclose(fp, sample["reference"], atol=1e-4, rtol=1e-4):
        raise AssertionError("FP64 replay does not match saved real FP32 head")
    input_only = softmax(qdq @ kdq.T / math.sqrt(q.shape[1]), allowed) @ vdq
    scores = np.array([r["scores_i16_f8"] for r in rows], dtype=np.float64) / 256
    score_only = softmax(scores, allowed) @ vdq
    probs = np.array([r["probabilities"] for r in rows], dtype=np.float64) / (2 ** pbits - 1)
    probability_only = probs @ vdq
    actual = np.array([r["output_i16_f12"] for r in rows], dtype=np.float64) / 4096
    # Deliberately wrong implementations preserve the first block scale for all tokens.
    wrong_k = ki.astype(np.float64) * 2.0 ** ke[0]
    wrong_score = softmax(qdq @ wrong_k.T / math.sqrt(q.shape[1]), allowed) @ vdq
    wrong_v = probs @ (vi.astype(np.float64) * 2.0 ** ve[0])
    negative = []
    for label, exponents, wrong, reference in (
        ("pull_K_scale_outside_softmax", ke, wrong_score, input_only),
        ("pull_V_scale_outside_PV_sum", ve, wrong_v, probability_only)):
        applicable = len(set(exponents)) > 1
        detected = bool(not np.allclose(wrong, reference, atol=1e-8, rtol=1e-8))
        negative.append({"name": label, "applicable": applicable,
                         "detected": detected if applicable else None,
                         "error": error(wrong, reference),
                         "note": "equal exponents are a genuine non-counterexample" if not applicable else ""})
    report = {"name": name, "input_profile": profile,
        "balance_exponents_i8": balance.tolist(),
        "offline_float_transform_elements": int((q.size+k.size) if profile != "direct" else 0),
        "extra_balance_metadata_bytes": int(balance.nbytes if profile != "direct" else 0),
        "transform_integer_hardware_implemented": False,
        "q_shape": list(q.shape), "kv_shape": list(k.shape), "block": block,
        "probability_bits": pbits, "q_exponents": qe, "k_exponents": ke, "v_exponents": ve,
        "quantization_clipped": clipped, "integer_values_checked": comparisons,
        "stage_errors": {"captured_float_vs_fp64": error(sample["reference"], fp),
            "input_quant_only_vs_float": error(input_only, fp), "score_rq_only": error(score_only, input_only),
            "lut_and_P_only": error(probability_only, score_only),
            "PV_output_rne_only": error(actual, probability_only), "total_vs_float": error(actual, fp)},
        "negative_controls": negative, "counts": counts,
        "max_abs_qk_i32": max(abs(x) for row in rows for x in row["qk_i32"]),
        "max_abs_pv_partial_i32": max(abs(x) for row in rows for p in row["partials_i32"] for x in p),
        "max_abs_aligned_i64": max(abs(x) for row in rows for x in row["aligned_i64"]),
        "logical_bytes": {"Q_i8": int(qi.nbytes), "K_i8": int(ki.nbytes), "V_i8": int(vi.nbytes),
            "Q_scale_i8": len(qe), "K_V_scale_i8": len(ke)+len(ve),
            "score_M_u32_r_u8": len(qe)*len(ke)*5,
            "balance_exponent_i8": len(balance) if profile != "direct" else 0,
            "score_i16": len(q)*len(k)*2, "probability_i8_or_i16": len(q)*len(k)*(1 if pbits==7 else 2),
            "PV_all_partials_i32_if_materialized": len(q)*len(ve)*v.shape[1]*4,
            "PV_i64_accumulator_full_query_tile": len(q)*v.shape[1]*8,
            "exp_ROM_u32": 4097*4},
        "probability_sums": [row["softmax"]["sum_probability_int"] for row in rows],
        "scope": "actual single Qwen3 layer0/head0 short capture; offline full-block scales; no full-model quality"}
    payload = {"name": name, "input_profile": profile, "block": block, "probability_bits": pbits,
        "q_i8": qi.tolist(), "k_i8": ki.tolist(), "v_i8": vi.tolist(),
        "k_exponents": ke, "v_exponents": ve, "q_exponents": qe,
        "score_M_r": params, "allowed": allowed.tolist(), "rows": rows}
    return report, payload


def transport(config):
    """Boundary service model only. Same one reducer/accumulator and staging capacity."""
    c = config["transport"]; d = c["dimension"]; beat = c["beat_bytes"]
    header = c["packet_header_bytes"]
    def physical(payload):
        return ((header + payload + beat - 1) // beat) * beat
    # Whole rows only; packet staging includes header and exponent. No unlimited FIFO.
    maximum_rows = (c["staging_bytes"] - header - 1) // (4 * d)
    records = []
    for total in c["rows"]:
        for blocks in (1, 2, 4, 8):
            groups = [min(maximum_rows, total - start) for start in range(0, total, maximum_rows)]
            # Local sends final Q12 row(s), exponent fixed in interface; remote sends per-block i32 + i8 exponent.
            local = sum(physical(rows * d * 2) for rows in groups)
            shared = blocks * sum(physical(rows * d * 4 + 1) for rows in groups)
            maximum_packet = max(physical(rows * d * 4 + 1) for rows in groups)
            acc_bytes = max(groups) * d * 8
            assert maximum_packet <= c["staging_bytes"] and acc_bytes <= c["accumulator_bytes"]
            # A single 1RW staging bank serializes a write and a read per beat.
            records.append({"rows": total, "value_dimension": d, "kv_blocks": blocks,
                "row_microtiles": groups, "near_reducer_physical_bytes": local,
                "shared_reducer_physical_bytes": shared,
                "near_link_service_cycles": local // c["bytes_per_cycle"],
                "shared_link_service_cycles": shared // c["bytes_per_cycle"],
                "near_staging_1RW_beat_accesses": 2 * local // beat,
                "shared_staging_1RW_beat_accesses": 2 * shared // beat,
                "max_packet_bytes": maximum_packet, "active_i64_accumulator_bytes": acc_bytes,
                "same_inventory": "one reducer, same 32KiB accumulator + 2KiB staging; interface ports assumed",
                "scope": "serial boundary-service accounting, not end-to-end latency or physical feasibility"})
    return records


def bias_experiment():
    counts = Counter(); rows = []
    for acc, bias in ((2**31-1, 2**31-1), (-2**31, -2**31), (3, 2), (-3, -2)):
        total = checked(acc + bias, 33)
        value = requant_wide(total, 1, 25, 8, 33, counts)
        expected = max(-128, min(127, round(Fraction(total, 2**25))))
        assert value == expected
        wrap = ((total + 2**31) % 2**32) - 2**31
        wrong = max(-128, min(127, round(Fraction(wrap, 2**25))))
        rows.append({"acc_i32": acc, "bias_i32": bias, "sum_i33": total,
                     "output_i8": value, "wrong_wrapping_i32_output": wrong,
                     "wrap_detected": value != wrong})
    # Same real bias requires a different integer bias when row activation scale changes.
    b = Fraction(1, 2); sw = Fraction(1, 32); sy = Fraction(1, 128)
    dynamic = []
    first_bias = None
    for sa in (Fraction(1, 64), Fraction(1, 16), Fraction(1, 4)):
        ib = round(b / (sa * sw)); checked(ib, 32)
        first_bias = ib if first_bias is None else first_bias
        m, r = compile_ratio(float(sa * sw / sy))
        actual = requant_wide(checked(10 + ib, 33), m, r, 8, 33, counts)
        wrong = requant_wide(10 + first_bias, m, r, 8, 33, counts)
        dynamic.append({"sa": str(sa), "sw": str(sw), "bias_real": str(b),
            "bias_acc_i32": ib, "M": m, "r": r, "output_i8": actual,
            "wrong_row0_bias_output_i8": wrong, "detected": actual != wrong})
    return {"scope": "synthetic bias contract; Qwen3 has no captured QKV bias", "boundary": rows,
        "dynamic_scale": dynamic, "counts": dict(counts),
        "implementation": "checked i33 add + 33xunsigned31 radix128 mul (25 signed8 partials), i64 accumulation, RNE then saturate; offline bias and M/r compile; no RQ33 RTL/PPA"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--development", action="store_true")
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("refuse to overwrite existing output")
    producer = source_record(args.development)
    cfg = json.loads((HERE / "experiment.json").read_text())
    data = (ROOT / cfg["source_archive"]).read_bytes()
    if sha(data) != cfg["source_archive_sha256"]:
        raise ValueError("original archive SHA mismatch")
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        raw = z.read(cfg["capture_member"])
        original_manifest = json.loads(z.read("capture/manifest.json"))
        input_tokens = json.loads(z.read("capture/inputs.json"))
    if sha(raw) != cfg["capture_sha256"]:
        raise ValueError("original real capture SHA mismatch")
    args.output.mkdir(parents=True)
    archive = np.load(io.BytesIO(raw), allow_pickle=False)
    table = load()["exp_u32_f24"]
    reports, payload = [], []
    for name in cfg["captures"]:
        sample = {n: archive[name + "." + n] for n in ("query", "key", "value", "query_positions",
                  "additive_mask", "mask_present", "reference")}
        for block in cfg["block_tokens"]:
            for bits in cfg["probability_bits"]:
                for profile in cfg["input_profiles"]:
                    report, values = evaluate(name, sample, block, bits, profile, table)
                    reports.append(report); payload.append(values)
    save(args.output / "numeric.json", reports)
    # Compact full integer payload allows independent auditing without new model downloads.
    (args.output / "integers.json").write_text(json.dumps(payload, separators=(",", ":"), allow_nan=False) + "\n",
                                             encoding="utf-8", newline="\n")
    save(args.output / "transport.json", transport(cfg))
    save(args.output / "bias.json", bias_experiment())
    negatives = [n for r in reports for n in r["negative_controls"]]
    summary = {"cases": len(reports), "integer_values_checked": sum(r["integer_values_checked"] for r in reports),
        "integer_mismatches": 0, "overflow_exceptions": 0,
        "applicable_negative_controls": sum(n["applicable"] for n in negatives),
        "detected_negative_controls": sum(n["detected"] is True for n in negatives),
        "nonapplicable_negative_controls": sum(not n["applicable"] for n in negatives),
        "maximum_total_relative_rmse": max(r["stage_errors"]["total_vs_float"]["relative_rmse"] for r in reports),
        "note": "not a full-model quality or speed acceptance; scales chosen from these observed blocks"}
    save(args.output / "summary.json", summary)
    unchanged = all(sha((ROOT / path).read_bytes()) == record["sha256"]
                    for path, record in producer["files"].items())
    if not unchanged or git("rev-parse", "HEAD") != producer["commit"]:
        raise ValueError("source changed during run")
    manifest = {"producer": producer, "config_sha256": sha((HERE / "experiment.json").read_bytes()),
        "input": {"archive_sha256": sha(data), "capture_sha256": sha(raw),
            "original_model_revision": cfg["model_revision"], "original_capture_commit": cfg["original_capture_commit"],
            "original_model_files": original_manifest["model_files"],
            "input_token_sha256": input_tokens["token_bytes_sha256"],
            "selection": "existing layer0 Qhead0/KVhead0, post norm/RoPE; prefill32 and final decode48"},
        "source_unchanged": unchanged,
        "files": {p.name: {"bytes": p.stat().st_size, "sha256": sha(p.read_bytes())}
                  for p in sorted(args.output.iterdir()) if p.is_file()}}
    save(args.output / "manifest.json", manifest)
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
