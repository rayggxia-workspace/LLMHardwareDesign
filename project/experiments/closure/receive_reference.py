"""Independent Issue72 Granite route-reference receipt.

Recomputes complete-router linear forward-error bounds, actual-logit top8 and
softmax, all layer/LM trace comparisons and unchanged gates. It does not reload
the full model and cannot certify all attention/expert arithmetic or quality.
"""
import argparse
import math
from pathlib import Path
import shutil
import zipfile
import io

import numpy as np

from audit_io import (need, load_json, save_json, sha, descriptor,
                      verify_manifest, check_source, replace_artifact_hash)

GATE = {"relative_l2_max": 2e-4, "max_abs_max": 2e-3}
REVISION = "a02780686e08a03fe0d2679a293b5c74a90efa89"
PROFILES = ("full", "cached64", "chunk16")


def arrays(path):
    with np.load(path, allow_pickle=False) as z:
        result = {k: z[k] for k in z.files}
    need(all(not x.dtype.hasobject for x in result.values()), "no object arrays")
    return result


def metric(a, reference):
    x, y = np.asarray(a, np.float64), np.asarray(reference, np.float64)
    need(x.shape == y.shape and x.size > 0 and np.isfinite(x).all()
         and np.isfinite(y).all(), "finite matching metric tensors")
    delta = x - y
    return dict(relative_l2=float(np.sqrt(np.sum(delta * delta)) /
                                 max(float(np.sqrt(np.sum(y * y))), 1e-30)),
                max_abs=float(np.max(np.abs(delta))))


def equal_metric(wanted, actual):
    need(set(wanted) == set(actual), "metric keys")
    for name, value in actual.items():
        need(math.isclose(float(wanted[name]), value, rel_tol=2e-11, abs_tol=1e-13),
             "independent metric " + name)


def route_summary(logits, ids, stable):
    x, chosen = np.asarray(logits), np.asarray(ids)
    need(x.ndim == 2 and x.shape[1] == 40 and chosen.shape == (len(x), 8)
         and np.issubdtype(chosen.dtype, np.integer) and np.isfinite(x).all(),
         "complete40/top8 shape/dtype")
    need(np.all((chosen >= 0) & (chosen < 40)), "expert index")
    for values, selected in zip(x, chosen):
        need(len(set(map(int, selected))) == 8, "unique experts")
        if stable:
            expected = sorted(range(40), key=lambda i: (-float(values[i]), i))[:8]
            need(list(map(int, selected)) == expected, "stable exact-score router")
        else:
            need(np.array_equal(np.sort(values[selected]), np.sort(values)[-8:]),
                 "native actual-logit top8")
    sorted_x = np.sort(x, axis=1)
    margins = sorted_x[:, -8] - sorted_x[:, -9]
    return {"top8_margin": margins.tolist(), "minimum_top8_margin": float(min(margins)),
            "exact_cutoff_tie_tokens": int(np.count_nonzero(margins == 0)),
            "any_exact_logit_tie_tokens": int(np.count_nonzero(np.any(np.diff(sorted_x, axis=1) == 0, axis=1)))}


def verify_router(x, w, logits, ids, weights, precision):
    dtype_x = np.float64 if precision == "model64" else np.float32
    dtype_logit = np.float32 if precision == "native32" else np.float64
    need(x.dtype == dtype_x and w.dtype == dtype_x and logits.dtype == dtype_logit
         and weights.dtype == dtype_x and x.ndim == 2 and w.shape == (40, x.shape[1])
         and logits.shape == (len(x), 40) and weights.shape == ids.shape,
         "observed reference precision/shape")
    need(np.isfinite(x).all() and np.isfinite(w).all() and np.isfinite(weights).all(),
         "router finite")
    xd, wd = x.astype(np.float64), w.astype(np.float64)
    expected = xd @ wd.T
    magnitude = np.abs(xd) @ np.abs(wd).T
    epsilon = np.finfo(dtype_logit).eps
    operations = 2 * x.shape[1] + 2
    need(operations * epsilon < 1, "forward error bound defined")
    gamma = operations * epsilon / (1 - operations * epsilon)
    allowance = gamma * magnitude + np.finfo(dtype_logit).tiny * operations
    need(np.all(np.abs(expected - logits) <= allowance), "router independent linear bound")
    summary = route_summary(logits, ids, precision != "native32")
    selected = np.take_along_axis(logits.astype(np.float64), ids, 1)
    exponent = np.exp(selected - np.max(selected, axis=1, keepdims=True))
    probabilities = exponent / np.sum(exponent, axis=1, keepdims=True)
    need(np.all(np.abs(probabilities - weights) <= 8 * np.finfo(dtype_x).eps),
         "selected softmax/cast")
    # An independent scalar correctly rounded summation at the most sensitive
    # token of every layer/profile supplements the different BLAS computation.
    token = int(np.argmin(summary["top8_margin"]))
    for expert in range(40):
        value = math.fsum(float(a) * float(b) for a, b in zip(x[token], w[expert]))
        need(abs(value - float(logits[token, expert])) <= float(allowance[token, expert]),
             "router scalar fsum bound")
    return summary


def verify(folder, original_folder, producer_source):
    folder, original_folder = Path(folder), Path(original_folder)
    m, checked = verify_manifest(folder, kind="granite_reference72", statuses=("EXECUTED_REFERENCE",))
    check_source(m, producer_source, "granite_reference_sha256")
    original, original_checked = verify_manifest(original_folder, kind="granite_capture", statuses=("FAIL",))
    need(m["model_revision"] == original["model_revision"] == REVISION,
         "pinned revision")
    need(m["original_capture"]["status"] == "FAIL"
         and m["original_capture"]["manifest_sha256"] == sha(original_folder / "manifest.json"),
         "original failure retained")
    need(m["model_files"] == original["model_files"], "original model SHA index")
    need(m["implementation"]["sha256"] == original["implementation"]["sha256"]
         == sha(folder / "granitemoe-implementation.py"), "framework source unchanged")
    precision = m["precision_variant"]
    need(precision in ("native32", "router64", "model64"), "reference variant")
    report, z = load_json(folder / "report.json"), arrays(folder / "trace.npz")
    need(report["precision_variant"] == precision and report["unchanged_gate"] == GATE
         and report["original_capture_status"] == "FAIL", "unchanged reference gate")
    all_passed, comparisons, scalar_dots = True, {}, 0
    expected_keys = {"router_weight." + str(i) for i in range(32)}
    for case in ("calibration", "evaluation"):
        expected_keys.add(case + ".tokens")
        token_ids = original["cases"][case]["tokens"]
        need(z[case + ".tokens"].dtype == np.int64
             and z[case + ".tokens"].tolist() == token_ids == report["cases"][case]["tokens"]
             and len(token_ids) == 72, "frozen case tokens")
        for profile in PROFILES:
            prefix = case + "." + profile + "."
            lm = z[prefix + "lm_logits"]
            expected_keys.add(prefix + "lm_logits")
            need(lm.ndim == 2 and lm.shape[0] == 72 and np.isfinite(lm).all(), "complete LM trace")
            wanted_spans = ([[0, 72]] if profile == "full" else [[0, 64]] + [[t, t + 1] for t in range(64, 72)]
                            if profile == "cached64" else [[t, min(t + 16, 72)] for t in range(0, 72, 16)])
            run = report["cases"][case]["runs"][profile]
            need(run["cache_spans"] == wanted_spans, "continuous profile spans")
            for layer in range(32):
                base = prefix + str(layer) + "."
                fields = ("router_input", "logits", "ids", "weights", "moe_output", "hidden")
                expected_keys.update(base + field for field in fields)
                x, logits, ids, weights = (z[base + field] for field in fields[:4])
                need(x.shape == (72, 1536) and z[base + "moe_output"].shape == (72, 1536)
                     and z[base + "hidden"].shape == (72, 1536), "complete layer trace")
                summary = verify_router(x, z["router_weight." + str(layer)], logits, ids, weights, precision)
                scalar_dots += 40
                need(run["router_summaries"][str(layer)] == summary, "reported margin/ties")
                observed = run["router_observed_dtypes"][str(layer)]
                expected_types = {"input": "torch.float64" if precision == "model64" else "torch.float32",
                                  "weight": "torch.float64" if precision == "model64" else "torch.float32",
                                  "logits": "torch.float32" if precision == "native32" else "torch.float64",
                                  "softmax_return": "torch.float64" if precision == "model64" else "torch.float32"}
                need(observed == expected_types, "reported observed router dtypes")
        comparisons[case] = {}
        for profile in ("cached64", "chunk16"):
            c = report["cases"][case]["comparisons"][profile]
            err = metric(z[case + "." + profile + ".lm_logits"], z[case + ".full.lm_logits"])
            equal_metric(c["lm_error"], err)
            passed = err["relative_l2"] <= GATE["relative_l2_max"] and err["max_abs"] <= GATE["max_abs_max"]
            need(c["passes_unchanged_gate"] is passed, "reported reference gate")
            all_passed = all_passed and passed
            need(len(c["layers"]) == 32, "all layer comparison records")
            total = 0
            for layer, row in enumerate(c["layers"]):
                need(row["layer"] == layer, "layer comparison order")
                p, q = case + ".full." + str(layer) + ".", case + "." + profile + "." + str(layer) + "."
                first, other = z[p + "ids"], z[q + "ids"]
                changed = [len(set(map(int, a)) ^ set(map(int, b))) // 2 for a, b in zip(first, other)]
                changes = int(np.count_nonzero(changed))
                need(row["replaced_experts"] == changed and row["set_changed_tokens"] == changes
                     and row["ordered_changed_tokens"] == int(np.count_nonzero(np.any(first != other, axis=1))),
                     "actual route changes")
                total += changes
                for target, field in (("logits_error", "logits"), ("router_input_error", "router_input"),
                                      ("moe_output_error", "moe_output"), ("layer_hidden_error", "hidden")):
                    equal_metric(row[target], metric(z[q + field], z[p + field]))
                need(row["full"] == route_summary(z[p + "logits"], first, precision != "native32")
                     and row["other"] == route_summary(z[q + "logits"], other, precision != "native32"),
                     "comparison margins")
            need(c["total_layer_token_set_changes"] == total, "total changed layer-token count")
            comparisons[case][profile] = dict(error=err, gate_passed=passed, layer_token_set_changes=total)
    need(set(z) == expected_keys, "complete exact trace key index")
    qualification = "PASS" if all_passed else "FAIL"
    need(report["reference_self_consistency"] == m["reference_self_consistency"] == qualification,
         "reference qualification")
    return {"status": "PASS", "precision_variant": precision,
            "reference_self_consistency": qualification, "original_capture_status": "FAIL",
            "artifacts": checked, "original_artifacts_checked": len(original_checked),
            "router_profile_layers": 192, "independent_scalar_complete_dots": scalar_dots,
            "comparisons": comparisons,
            "limits": ["Receiver validates router math, provenance and published trace comparisons; does not rerun full attention/expert model",
                       "Floating reference arithmetic; no integer deployment or model application quality acceptance",
                       "Original Issue70 failure retained even when a new precision reference passes"]}


def rewrite_npz_member(path, key, mutate):
    path = Path(path)
    temporary = path.with_suffix(".negative-part")
    with zipfile.ZipFile(path) as src, zipfile.ZipFile(temporary, "x", zipfile.ZIP_DEFLATED) as dst:
        for item in src.infolist():
            raw = src.read(item.filename)
            if item.filename == key + ".npy":
                value = np.load(io.BytesIO(raw), allow_pickle=False)
                value = mutate(value.copy())
                buffer = io.BytesIO()
                np.save(buffer, value, allow_pickle=False)
                raw = buffer.getvalue()
            dst.writestr(item.filename, raw)
    temporary.replace(path)


def negatives(folder, original, producer, out):
    """Actual artifact mutation + new artifact SHA; semantic detection required."""
    result = []
    for label in ("logit", "route", "qualification"):
        scratch = Path(out) / ("negative-" + label)
        shutil.copytree(folder, scratch)
        if label == "logit":
            def corrupt(x):
                x[0, 0] += 100
                return x
            rewrite_npz_member(scratch / "trace.npz", "evaluation.full.0.logits", corrupt)
            replace_artifact_hash(scratch, "trace.npz")
        elif label == "route":
            def corrupt(x):
                x[0, 1] = x[0, 0]
                return x
            rewrite_npz_member(scratch / "trace.npz", "evaluation.full.0.ids", corrupt)
            replace_artifact_hash(scratch, "trace.npz")
        else:
            report = load_json(scratch / "report.json")
            report["reference_self_consistency"] = "FAIL" if report["reference_self_consistency"] == "PASS" else "PASS"
            save_json(scratch / "report.json", report)
            replace_artifact_hash(scratch, "report.json")
        # Prove the updated container passes hashes before requiring rejection.
        verify_manifest(scratch, kind="granite_reference72", statuses=("EXECUTED_REFERENCE",))
        try:
            verify(scratch, original, producer)
        except (ValueError, AssertionError) as error:
            result.append(dict(case=label, hash_rewritten=True, artifact_hash_layer_passed=True,
                               semantic_rejected=True, reason=str(error),
                               mutated_manifest=descriptor(scratch / "manifest.json")))
        else:
            raise ValueError("semantic negative accepted: " + label)
    return result


def main():
    p = argparse.ArgumentParser(__doc__)
    p.add_argument("--result", type=Path, required=True)
    p.add_argument("--original", type=Path, required=True)
    p.add_argument("--producer-source", type=Path, required=True)
    p.add_argument("--binding", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--skip-negatives", action="store_true")
    args = p.parse_args()
    need(not args.out.exists(), "refuse output overwrite")
    binding = load_json(args.binding)
    need(binding.get("receive_reference_sha256") == sha(__file__) and binding.get("commit"),
         "receiver source binding")
    need(binding.get("audit_io_sha256") == sha(Path(__file__).with_name("audit_io.py")),
         "receiver IO dependency source binding")
    args.out.mkdir(parents=True)
    receipt = verify(args.result, args.original, args.producer_source)
    receipt.update(receiver=binding, producer_manifest=descriptor(args.result / "manifest.json"))
    receipt["semantic_negatives"] = [] if args.skip_negatives else negatives(args.result, args.original, args.producer_source, args.out)
    if args.skip_negatives:
        receipt["status"] = "PARTIAL_NO_NEGATIVES"
    save_json(args.out / "receipt.json", receipt)
    print(receipt["status"], receipt["reference_self_consistency"], flush=True)


if __name__ == "__main__":
    main()
