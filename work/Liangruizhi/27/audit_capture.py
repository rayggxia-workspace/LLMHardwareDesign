"""Independent read-only capture audit: no capture/online_attention imports.

Recompute full attention and each prefix's unnormalized state directly from raw
Q/K/V/mask. Never load or execute model weights; hash their existing bytes only.
"""
import argparse
import hashlib
import importlib.metadata
import json
import math
from pathlib import Path
import subprocess
import sys
import traceback
import zipfile

import numpy as np


EXPECTED_SOURCE = "6ffb9417f0f01f614b733ce6c3ca9837906b3203"
EXPECTED_CAPTURE = "57f8c08c07d0b9ab679e26643f8ce86ccbaeebe9fcdf65686acf9aec7bf419a4"
EXPECTED_CONFIG = "6aa8da27a8d85374c84a592365df2597acf6b20d3d979fac1bed000559913482"
EXPECTED_REVISION = "c1899de289a04d12100db370d81485cdf75e47ca"
ATOL = RTOL = 1e-4


def digest(data):
    return hashlib.sha256(data).hexdigest()


FILE_CACHE = {}


def file_record(path):
    path = Path(path).resolve()
    if str(path) not in FILE_CACHE:
        h = hashlib.sha256()
        with path.open("rb") as stream:
            for data in iter(lambda: stream.read(8 * 1024 * 1024), b""):
                h.update(data)
        FILE_CACHE[str(path)] = {"bytes": path.stat().st_size, "sha256": h.hexdigest()}
    return FILE_CACHE[str(path)]


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def metrics(actual, expected):
    a, b = np.asarray(actual, dtype=np.float64), np.asarray(expected, dtype=np.float64)
    finite = bool(np.isfinite(a).all() and np.isfinite(b).all())
    if not finite or a.shape != b.shape:
        return {"pass": False, "allfinite": finite, "max_abs": None, "relative_l2": None}
    error, norm = float(np.linalg.norm(a - b)), float(np.linalg.norm(b))
    return {"pass": bool(np.all(np.abs(a - b) <= ATOL + RTOL * np.abs(b))),
            "allfinite": finite, "max_abs": float(np.max(np.abs(a - b))),
            "relative_l2": error / norm if norm else (0.0 if not error else None)}


def direct_prefix(scores, values, end):
    """Full materialized prefix softmax; no online m/l/O recurrence."""
    subset = scores[:, :end]
    maxima = np.max(subset, axis=1)
    exponentials = np.exp(subset - maxima[:, None])
    normalizers = np.sum(exponentials, axis=1)
    unnormalized = np.einsum("qk,kd->qd", exponentials, values[:end], optimize=False)
    return maxima, normalizers, unnormalized


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", type=Path, default=Path("D:/Projects/Codex/state-port-study-20261022"))
    parser.add_argument("--issue23", type=Path, default=Path("D:/Projects/LLMHardwareDesign-inference/project/experiments/qwen3_trace/results/issue-23-run01"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("refusing to overwrite an audit report")
    report = {"audit": "independent-materialized-softmax-and-capture-provenance-v1",
              "status": "FAIL", "script": file_record(__file__), "command": sys.argv,
              "scope": "Read-only hashes and full-softmax recomputation of saved single-head tensors; no model execution, no proof of all-head/model or hardware-cycle/PPA validity.",
              "checks": [], "runs": {}}

    def check(name, passed, **details):
        report["checks"].append({"name": name, "pass": bool(passed), **details})

    archive_index = read_json(args.issue23 / "archive-sha256.json")
    archive_path = args.issue23 / archive_index["archive"]
    check("Issue23.archive.sha256", file_record(archive_path) == {k: archive_index[k] for k in ("bytes", "sha256")})
    with zipfile.ZipFile(archive_path) as archive:
        member = next(m for m in archive_index["members"] if m["file"] == "inputs.json")
        original_raw = archive.read("inputs.json")
        check("Issue23.archived_inputs.sha256", len(original_raw) == member["bytes"] and digest(original_raw) == member["sha256"])
        original_inputs = json.loads(original_raw)
        old_manifest = json.loads(archive.read("manifest.json"))
    run_data = {}
    for number in (1, 2):
        label = f"capture-{number:02d}"
        directory = args.base / label
        run_report = {"direct_softmax": {}, "state_prefix_checks": [], "negative_checks": []}
        report["runs"][label] = run_report
        try:
            manifest = read_json(directory / "manifest.json")
            summary = read_json(directory / "numeric-results.json")
            inputs = read_json(directory / "inputs.json")
            start = read_json(directory / "manifest-start.json")
            check(f"{label}.formal_status_scope", manifest["status"] == summary["status"] == "PASS"
                  and manifest["development"] is False and manifest["source_commit"] == EXPECTED_SOURCE
                  and "independent NumPy-computed states" in summary["scope"]
                  and "Not all heads/layers/models" in summary["scope"])
            check(f"{label}.source_runtime_flags", manifest["source_dirty_at_start"] is False and all(
                manifest[name] is True for name in ("capture_source_in_recorded_commit", "source_unchanged_at_end",
                    "source_clean_at_end", "eager_callable_restored", "model_files_unchanged_at_end")))
            inventory = {p.name for p in directory.iterdir() if p.is_file()}
            check(f"{label}.complete_artifact_inventory", inventory == set(manifest["artifacts"]) | {"manifest.json"})
            for name, expected in manifest["artifacts"].items():
                check(f"{label}.artifact.{name}", file_record(directory / name) == expected)
            for name in ("profile", "development", "source_commit", "source_root", "source_files",
                         "source_commit_bindings", "model_id", "revision", "model_files"):
                check(f"{label}.start_end.{name}", start[name] == manifest[name])
            root = Path(manifest["source_root"])
            for binding in manifest["source_commit_bindings"]:
                path, relative = Path(binding["path"]), binding["git_path"]
                committed = subprocess.check_output(["git", "-C", str(root), "show", f"{EXPECTED_SOURCE}:{relative}"])
                actual = digest(committed)
                check(f"{label}.committed_source.{relative}", binding["in_commit"] is True
                    and binding["bytes_match_commit"] is True and actual == binding["commit_blob_sha256"]
                    == binding["worktree_sha256"] == manifest["source_files"][str(path)]
                    == file_record(path)["sha256"], sha256=actual)
            capture_binding = next(b for b in manifest["source_commit_bindings"] if b["git_path"].endswith("state_ports/capture.py"))
            config_binding = next(b for b in manifest["source_commit_bindings"] if b["git_path"].endswith("qwen3_trace/experiment.json"))
            check(f"{label}.frozen_capture_and_config", capture_binding["commit_blob_sha256"] == EXPECTED_CAPTURE
                  and config_binding["commit_blob_sha256"] == EXPECTED_CONFIG)
            config = read_json(config_binding["path"])
            check(f"{label}.model_identity", manifest["model_id"] == config["model_id"] == "Qwen/Qwen3-0.6B"
                  and manifest["revision"] == config["revision"] == old_manifest["revision"] == EXPECTED_REVISION
                  and manifest["model_files"] == config["model_files"] == old_manifest["model_files"]
                  and len(manifest["model_files"]) == 8)
            for name, expected in manifest["model_files"].items():
                check(f"{label}.actual_model_file.{name}", file_record(Path(manifest["local_weights_dir"]) / name) == expected)
            for name, expected in manifest["implementation_files"].items():
                check(f"{label}.installed_implementation.{name}", file_record(expected["path"])["sha256"] == expected["sha256"])
            check(f"{label}.runtime", manifest["runtime"]["threads"] == 4
                  and manifest["runtime"]["interop_threads"] == 1 and manifest["runtime"]["dtype"] == "float32"
                  and manifest["runtime"]["device"] == "cpu" and manifest["runtime"]["attention"] == "eager"
                  and manifest["runtime"]["deterministic_algorithms"] is True)
            for name, version in manifest["packages"].items():
                check(f"{label}.installed_package.{name}", importlib.metadata.version(name) == version)
            selection = manifest["selection"]
            check(f"{label}.single_head_scope", (selection["layer"], selection["query_head"], selection["kv_head"],
                  selection["GQA_Q_heads_per_KV_head"]) == (0, 0, 0, 2))
            ids = np.array(inputs["token_ids"], dtype=np.int64)
            check(f"{label}.teacher_forced_original_tokens", ids.shape == (1, 48)
                  and inputs["token_ids"] == [original_inputs["token_ids"][0][:48]]
                  and inputs["text"] == original_inputs["text"] == config["input_text"]
                  and inputs["teacher_forced"] is True and inputs["generation"] is False
                  and inputs["add_special_tokens"] is False and inputs["prefix"] == 32 and inputs["steps"] == 16
                  and digest(ids.tobytes()) == inputs["token_bytes_sha256"])
            with np.load(directory / "attention-stages.npz", allow_pickle=False) as npz:
                arrays = {name: npz[name] for name in npz.files}
            with zipfile.ZipFile(directory / "attention-stages.npz") as archive:
                check(f"{label}.npz_unique_members", len(archive.namelist()) == len(set(archive.namelist()))
                      and set(archive.namelist()) == {name + ".npy" for name in arrays})
            expected_shapes = {}
            for capture, qlength, klength in (("prefill32", 32, 32), ("decode48", 1, 48)):
                for field in ("query", "reference"):
                    expected_shapes[f"{capture}.{field}"] = ([qlength, 128], "float32")
                for field in ("key", "value"):
                    expected_shapes[f"{capture}.{field}"] = ([klength, 128], "float32")
                expected_shapes.update({f"{capture}.additive_mask": ([qlength, klength], "float32"),
                    f"{capture}.scaling": ([], "float32"), f"{capture}.mask_present": ([], "bool"),
                    f"{capture}.query_positions": ([qlength], "int64")})
                for tile in (8, 16, 32):
                    count = math.ceil(klength / tile)
                    expected_shapes[f"{capture}.tile{tile}.output"] = ([qlength, 128], "float32")
                    expected_shapes[f"{capture}.tile{tile}.O"] = ([count, qlength, 128], "float32")
                    for field in ("m", "l", "alpha"):
                        expected_shapes[f"{capture}.tile{tile}.{field}"] = ([count, qlength], "float32")
            check(f"{label}.npz_complete_stage_inventory", set(arrays) == set(summary["stages"]) == set(expected_shapes), members=len(arrays))
            for name, array in arrays.items():
                expected = summary["stages"][name]
                shape, dtype = expected_shapes[name]
                actual = {"shape": list(array.shape), "dtype": str(array.dtype), "bytes": array.nbytes,
                          "sha256": digest(array.tobytes(order="C"))}
                check(f"{label}.npz_member.{name}", actual == expected and actual["shape"] == shape
                      and actual["dtype"] == dtype and not array.dtype.hasobject and np.isfinite(array).all(), **actual)
            check(f"{label}.persistent_cache_prefix_bitwise", all(
                arrays[f"prefill32.{field}"].tobytes() == arrays[f"decode48.{field}"][:32].tobytes()
                for field in ("key", "value")))
            seen_records = set()
            positive_count = negative_count = not_applicable = 0
            for capture, qlength, klength in (("prefill32", 32, 32), ("decode48", 1, 48)):
                q = arrays[f"{capture}.query"].astype(np.float64)
                k = arrays[f"{capture}.key"].astype(np.float64)
                v = arrays[f"{capture}.value"].astype(np.float64)
                mask = arrays[f"{capture}.additive_mask"].astype(np.float64)
                scaling = float(arrays[f"{capture}.scaling"])
                positions = arrays[f"{capture}.query_positions"]
                allowed = np.arange(klength)[None, :] <= np.arange(klength - qlength, klength)[:, None]
                check(f"{label}.{capture}.causal_mask_positions_scale", bool(arrays[f"{capture}.mask_present"])
                      and np.array_equal(positions, np.arange(klength - qlength, klength))
                      and np.array_equal(mask == 0, allowed) and (mask[~allowed] < -1e20).all()
                      and scaling == float(np.float32(1 / math.sqrt(128))))
                scores = np.einsum("qd,kd->qk", q, k, optimize=False) * scaling + mask
                _, final_l, final_O = direct_prefix(scores, v, klength)
                full_output = final_O / final_l[:, None]
                actual_reference = arrays[f"{capture}.reference"]
                direct = metrics(full_output, actual_reference)
                run_report["direct_softmax"][capture] = direct
                check(f"{label}.{capture}.independent_full_softmax", direct["pass"], **direct)
                for tile in (8, 16, 32):
                    record = next(r for r in summary["records"] if (r["capture"], r["tile"]) == (capture, tile))
                    seen_records.add((capture, tile))
                    current = metrics(arrays[f"{capture}.tile{tile}.output"], actual_reference)
                    max_match = current["max_abs"] == record["comparison"]["max_abs"]
                    check(f"{label}.{capture}.tile{tile}.positive_record", record["passed"] is True
                          and record["comparison"]["pass"] is current["pass"] is True
                          and record["comparison"]["allfinite"] is True and record["allfinite_states"] is True
                          and record["tiles"] == math.ceil(klength / tile) and max_match)
                    positive_count += current["pass"]
                    previous_max = np.full(qlength, -np.inf)
                    contributions = []
                    for state_index, start_index in enumerate(range(0, klength, tile)):
                        end = min(klength, start_index + tile)
                        m, l, O = direct_prefix(scores, v, end)
                        alpha = np.exp(previous_max - m)
                        for field, expected in (("m", m), ("l", l), ("O", O), ("alpha", alpha)):
                            result = metrics(arrays[f"{capture}.tile{tile}.{field}"][state_index], expected)
                            run_report["state_prefix_checks"].append({"capture": capture, "tile": tile,
                                "prefix_keys": end, "field": field, **result})
                            check(f"{label}.{capture}.tile{tile}.prefix{end}.{field}", result["pass"])
                        local_P = np.exp(scores[:, start_index:end] - m[:, None])
                        contributions.append(np.einsum("qk,kd->qd", local_P, v[start_index:end], optimize=False))
                        previous_max = m
                    for control in record["negative_controls"]:
                        applicable = len(contributions) > 1
                        check(f"{label}.{capture}.tile{tile}.{control['name']}.scope", control["applicable"] is applicable)
                        if not applicable:
                            not_applicable += 1
                            check(f"{label}.{capture}.tile{tile}.{control['name']}.not_claimed_detected", "detected" not in control and bool(control.get("reason")))
                            continue
                        if control["name"] == "wrong_O_alpha_half":
                            wrong_O = sum((0.5 ** (len(contributions) - i - 1)) * T for i, T in enumerate(contributions))
                        elif control["name"] == "reset_O_each_tile":
                            wrong_O = contributions[-1]
                        else:
                            raise ValueError("unexpected negative control")
                        negative = metrics(wrong_O / final_l[:, None], actual_reference)
                        detected = negative["allfinite"] and not negative["pass"]
                        check(f"{label}.{capture}.tile{tile}.{control['name']}.independent_detected", detected
                            and control["detected"] is True and control["comparison"]["pass"] is False
                            and control["comparison"]["allfinite"] is True)
                        negative_count += detected
                        run_report["negative_checks"].append({"capture": capture, "tile": tile,
                            "name": control["name"], "detected": detected, **negative})
            check(f"{label}.exact_summary_counts", len(summary["records"]) == len(seen_records) == positive_count == 6
                  and negative_count == 10 and not_applicable == 2
                  and summary["positive_checks"] == summary["positive_passed"] == 6
                  and summary["negative_applicable"] == summary["negative_detected"] == 10
                  and summary["negative_not_applicable"] == 2)
            run_report.update(positive_checks=positive_count, negative_detected=negative_count,
                              negative_not_applicable=not_applicable, npz_members=len(arrays))
            run_data[label] = (manifest, summary, inputs, arrays)
        except Exception as exc:
            check(f"{label}.audit_exception", False, error=f"{type(exc).__name__}: {exc}", traceback=traceback.format_exc())
    if len(run_data) == 2:
        left, right = run_data["capture-01"], run_data["capture-02"]
        check("repeat_capture.raw_members_bitwise", all(left[3][name].tobytes() == right[3][name].tobytes()
              and left[3][name].dtype == right[3][name].dtype and left[3][name].shape == right[3][name].shape for name in left[3]))
        check("repeat_capture.artifacts_identical", all(file_record(args.base / "capture-01" / name)
            == file_record(args.base / "capture-02" / name) for name in ("attention-stages.npz", "inputs.json", "numeric-results.json")))
        check("repeat_capture.source_model_runtime_identical", all(left[0][name] == right[0][name] for name in (
              "source_commit", "source_files", "source_commit_bindings", "model_files", "runtime", "packages",
              "implementation_files", "selection", "dimensions")))
    failures = [check for check in report["checks"] if not check["pass"]]
    report["failures"] = failures
    report["totals"] = {"checks": len(report["checks"]), "passed": len(report["checks"]) - len(failures), "failed": len(failures)}
    report["status"] = "PASS" if not failures else "FAIL"
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "totals": report["totals"], "report": str(args.output), "failures": failures}, allow_nan=False))
    return not failures


if __name__ == "__main__":
    raise SystemExit(0 if main() else 1)
