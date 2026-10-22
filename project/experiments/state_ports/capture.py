"""Capture two real Qwen3 head boundaries and check independent online attention.

Default formal location: project/experiments/state_ports/capture.py. Development
outside a repository requires --development --config /path/to/frozen/config.
No result here calibrates an accelerator's cycles, power or physical feasibility.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import importlib.metadata
import inspect
import json
import math
from pathlib import Path
import platform
import subprocess
import sys
import time
import traceback


PROFILE = "qwen3-single-head-real-input-online-attention-v1"
CONFIG_SHA256 = "6aa8da27a8d85374c84a592365df2597acf6b20d3d979fac1bed000559913482"
IMPLEMENTATION_SHA256 = {
    "qwen3": "4b95c371fd26d40c69083dab36ac1eafd8cf82b415a0bb827275097c5ad2305b",
    "cache": "f4e11caf14c75bdefa5e3003b93ef0e8b97fb6103375705ad944b0b344d7da8a",
}
MODEL_FILES = ("config.json", "generation_config.json", "tokenizer.json", "tokenizer_config.json",
               "merges.txt", "vocab.json", "LICENSE", "model.safetensors")


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def save(path, value):
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


def _repo(path):
    return Path(git(path, "rev-parse", "--show-toplevel")).resolve()


def source_commit_binding(root, path, commit):
    """Bind actual raw bytes to a tracked commit blob, not just git status."""
    path = Path(path).resolve()
    record = {"path": str(path), "worktree_sha256": sha256(path), "in_commit": False}
    if not path.is_relative_to(root):
        return record
    relative = path.relative_to(root).as_posix()
    record["git_path"] = relative
    try:
        blob = subprocess.check_output(["git", "-C", str(root), "show", f"{commit}:{relative}"], stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError:
        return record
    record.update(in_commit=True, commit_blob_sha256=hashlib.sha256(blob).hexdigest())
    record["bytes_match_commit"] = record["commit_blob_sha256"] == record["worktree_sha256"]
    return record


def _metrics(actual, reference, atol=1e-4, rtol=1e-4):
    import numpy as np

    finite = bool(np.isfinite(actual).all() and np.isfinite(reference).all())
    record = {"pass": False, "allfinite": finite, "shape": list(actual.shape),
              "reference_shape": list(reference.shape), "max_abs": None, "relative_l2": None}
    if actual.shape != reference.shape or not finite:
        return record
    left, right = actual.astype(np.float64), reference.astype(np.float64)
    delta = left - right
    norm = float(np.linalg.norm(right))
    error = float(np.linalg.norm(delta))
    record.update(max_abs=float(np.max(np.abs(delta))),
                  relative_l2=error / norm if norm else (0.0 if not error else None),
                  **{"pass": bool(np.allclose(actual, reference, atol=atol, rtol=rtol, equal_nan=False))})
    return record


def online_attention(query, key, value, additive_mask, scaling, tile, *, mutation=None):
    """FP32 unnormalized online softmax, independent of Torch eager arithmetic.

    Inputs are one query head [Q,D], its actual grouped cache head [K,D], and
    its real additive mask [Q,K] or None. Returned states are small tile snapshots.
    """
    import numpy as np

    if isinstance(tile, bool) or not isinstance(tile, int) or tile <= 0:
        raise ValueError("tile must be a positive integer")
    if mutation not in (None, "wrong_O_alpha_half", "reset_O_each_tile"):
        raise ValueError("unknown controlled mutation")
    if (query.ndim != 2 or key.ndim != 2 or value.ndim != 2 or key.shape != value.shape
            or query.shape[1] != key.shape[1] or not query.shape[0] or not key.shape[0]
            or any(a.dtype != np.float32 or not np.isfinite(a).all() for a in (query, key, value))):
        raise ValueError("expected finite FP32 Q[Q,D],K/V[K,D]")
    if not math.isfinite(float(scaling)) or scaling <= 0:
        raise ValueError("invalid scaling")
    if additive_mask is not None and (additive_mask.shape != (query.shape[0], key.shape[0])
            or additive_mask.dtype != np.float32 or np.isnan(additive_mask).any()
            or np.isposinf(additive_mask).any()):
        raise ValueError("invalid additive mask")
    rows, dimension = query.shape
    m = np.full(rows, -np.inf, dtype=np.float32)
    l = np.zeros(rows, dtype=np.float32)
    O = np.zeros((rows, dimension), dtype=np.float32)
    states = []
    for start in range(0, key.shape[0], tile):
        end = min(start + tile, key.shape[0])
        scores = np.matmul(query, key[start:end].T) * np.float32(scaling)
        if additive_mask is not None:
            scores = scores + additive_mask[:, start:end]
        new_m = np.maximum(m, np.max(scores, axis=1))
        # Selected causal captures have >=1 allowed key in their first tile.
        # Reject an unsupported fully masked first row instead of creating NaNs.
        if not np.isfinite(new_m).all():
            raise ValueError("online profile requires at least one allowed first-tile key per row")
        alpha = np.exp(m - new_m).astype(np.float32, copy=False)
        P = np.exp(scores - new_m[:, None]).astype(np.float32, copy=False)
        new_l = alpha * l + np.sum(P, axis=1, dtype=np.float32)
        T = np.matmul(P, value[start:end])
        O_alpha = np.full_like(alpha, np.float32(0.5)) if mutation == "wrong_O_alpha_half" else alpha
        if mutation == "reset_O_each_tile":
            O = np.zeros_like(O)
        O = O_alpha[:, None] * O + T
        m, l = new_m, new_l
        states.append({"start": start, "end": end, "m": m.copy(), "l": l.copy(),
                       "O": O.copy(), "alpha": alpha.copy()})
    if not (np.isfinite(O).all() and np.isfinite(l).all() and (l > 0).all()):
        raise ValueError("nonfinite or zero online normalizer/state")
    return (O / l[:, None]).astype(np.float32), states


@contextmanager
def capture_eager(module_api, call_state, captures):
    """Single-process pass-through; always restore the exact prior callable."""
    import numpy as np
    import torch

    original = module_api.eager_attention_forward
    signature = inspect.signature(original)

    def array(tensor):
        if tensor.dtype != torch.float32 or tensor.device.type != "cpu":
            raise ValueError("observed tensor is not FP32 CPU")
        return tensor.detach().contiguous().numpy().copy()

    def wrapper(module, query, key, value, *args, **kwargs):
        selected = module.layer_idx == 0 and call_state.get("name") in ("prefill32", "decode48")
        sample = None
        if selected:
            name = call_state["name"]
            if name in captures:
                raise ValueError(f"duplicate selected head capture {name}")
            bound = signature.bind(module, query, key, value, *args, **kwargs)
            bound.apply_defaults()
            mask = bound.arguments.get("attention_mask")
            scaling = float(bound.arguments["scaling"])
            if float(bound.arguments.get("dropout", 0.0)) != 0.0 or module.training:
                raise ValueError("capture requires eval attention with zero dropout")
            qlength, klength = query.shape[-2], key.shape[-2]
            if list(query.shape) != [1, 16, qlength, 128] or list(key.shape) != [1, 8, klength, 128] or key.shape != value.shape:
                raise ValueError("unexpected Qwen3 GQA cache layout")
            if (qlength, klength) != ((32, 32) if name == "prefill32" else (1, 48)):
                raise ValueError("unexpected selected call lengths")
            positions = np.arange(klength - qlength, klength, dtype=np.int64)
            allowed = np.arange(klength)[None, :] <= positions[:, None]
            if mask is None:
                if qlength != 1:
                    raise ValueError("missing prefill causal mask")
                actual_mask = np.empty((0,), dtype=np.float32)
            else:
                if list(mask.shape) != [1, 1, qlength, klength]:
                    raise ValueError("unexpected real additive mask shape")
                actual_mask = array(mask[0, 0])
                if not (np.array_equal(actual_mask == 0, allowed)
                        and (actual_mask[~allowed] < -1e20).all()):
                    raise ValueError("real additive mask differs from the declared causal positions")
            sample = {
                "query": array(query[0, 0]), "key": array(key[0, 0]), "value": array(value[0, 0]),
                "additive_mask": actual_mask, "scaling": np.array(scaling, dtype=np.float32),
                "mask_present": np.array(mask is not None), "query_positions": positions,
            }
        # No replacement arithmetic and no tensor write precedes/follows this call.
        output = original(module, query, key, value, *args, **kwargs)
        if selected:
            if list(output[0].shape) != [1, query.shape[-2], 16, 128]:
                raise ValueError("eager output is not [batch,query,heads,dimension]")
            sample["reference"] = array(output[0][0, :, 0, :])
            captures[call_state["name"]] = sample
        return output

    try:
        module_api.eager_attention_forward = wrapper
        yield original
    finally:
        module_api.eager_attention_forward = original


def evaluate(captures, output):
    """Save observed stages and every positive/negative check, including failures."""
    import numpy as np

    records, archive = [], {}
    for name in ("prefill32", "decode48"):
        sample = captures[name]
        for field, array in sample.items():
            archive[f"{name}.{field}"] = array
        mask = sample["additive_mask"] if bool(sample["mask_present"]) else None
        for tile in (8, 16, 32):
            record = {"capture": name, "tile": tile, "passed": False, "negative_controls": []}
            records.append(record)
            try:
                actual, states = online_attention(sample["query"], sample["key"], sample["value"],
                                                  mask, float(sample["scaling"]), tile)
                record["comparison"] = _metrics(actual, sample["reference"])
                record["tiles"] = len(states)
                record["allfinite_states"] = all(np.isfinite(state[field]).all()
                    for state in states for field in ("O", "m", "l", "alpha"))
                record["allfinite_states"] = bool(record["allfinite_states"])
                archive[f"{name}.tile{tile}.output"] = actual
                for field in ("O", "m", "l", "alpha"):
                    archive[f"{name}.tile{tile}.{field}"] = np.stack([state[field] for state in states])
                for mutation in ("wrong_O_alpha_half", "reset_O_each_tile"):
                    control = {"name": mutation, "applicable": len(states) > 1}
                    record["negative_controls"].append(control)
                    if not control["applicable"]:
                        control["reason"] = "one KV tile has no previous nonzero O carry to corrupt"
                        continue
                    wrong, _ = online_attention(sample["query"], sample["key"], sample["value"],
                                                 mask, float(sample["scaling"]), tile, mutation=mutation)
                    metrics = _metrics(wrong, sample["reference"])
                    control.update(comparison=metrics, detected=metrics["allfinite"] and not metrics["pass"])
                record["passed"] = record["comparison"]["pass"] and record["allfinite_states"] and all(
                    not c["applicable"] or c.get("detected", False) for c in record["negative_controls"])
            except Exception as exc:
                record["error"] = f"{type(exc).__name__}: {exc}"
    np.savez_compressed(output / "attention-stages.npz", **archive)
    stages = {key: {"shape": list(value.shape), "dtype": str(value.dtype), "bytes": value.nbytes,
                    "sha256": hashlib.sha256(value.tobytes(order="C")).hexdigest()}
              for key, value in archive.items()}
    controls = [c for record in records for c in record["negative_controls"]]
    summary = {
        "profile": PROFILE, "status": "PASS" if all(r["passed"] for r in records) else "FAIL",
        "scope": "Actual layer0 query-head0 only, two shapes; Q/K/V/mask/reference are eager observations; tile m/l/O/alpha are independent NumPy-computed states. Not all heads/layers/models; no calibrated hardware cycles/PPA.",
        "tolerances": {"atol": 1e-4, "rtol": 1e-4}, "records": records,
        "positive_checks": len(records), "positive_passed": sum(r["passed"] for r in records),
        "negative_applicable": sum(c["applicable"] for c in controls),
        "negative_detected": sum(c.get("detected", False) for c in controls),
        "negative_not_applicable": sum(not c["applicable"] for c in controls),
        "stages": stages,
    }
    save(output / "numeric-results.json", summary)
    return summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--weights", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--development", action="store_true",
                        help="mark uncommitted/outside-repository development execution, never formal evidence")
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("refusing to replace an existing output directory")
    args.output.mkdir(parents=True)
    manifest = {"profile": PROFILE, "status": "ERROR", "development": args.development,
                "started_utc_epoch": time.time(), "command": sys.argv,
                "python": sys.version, "platform": platform.platform(), "artifacts": {}}
    original_eager = None
    model_files = None
    source_root = None
    script = Path(__file__).resolve()
    try:
        config_path = args.config
        if config_path is None:
            source_root = _repo(script.parent)
            config_path = source_root / "project/experiments/qwen3_trace/experiment.json"
        config_path = config_path.resolve()
        if sha256(config_path) != CONFIG_SHA256:
            raise ValueError("experiment config differs from the frozen Issue23 original")
        config = json.loads(config_path.read_text(encoding="utf-8"))
        source_root = source_root or _repo(config_path.parent)
        source_commit = git(source_root, "rev-parse", "HEAD")
        dirty = bool(git(source_root, "status", "--porcelain"))
        inside = script.is_relative_to(source_root)
        if not args.development and (dirty or not inside):
            raise ValueError("formal run requires this script inside a clean recorded repository")
        reference_dir = source_root / "project/experiments/qwen3_trace"
        source_files = {str(path): sha256(path) for path in (
            script, config_path, reference_dir / "run.py", reference_dir / "trace.py")}
        bindings = [source_commit_binding(source_root, path, source_commit) for path in source_files]
        if not args.development and not all(b.get("bytes_match_commit", False) for b in bindings):
            raise ValueError("formal source bytes are not all present and identical in the recorded commit")
        manifest.update(source_commit=source_commit, source_root=str(source_root), source_dirty_at_start=dirty,
                        capture_source_in_recorded_commit=bindings[0].get("bytes_match_commit", False),
                        source_files=source_files, source_commit_bindings=bindings,
                        model_id=config["model_id"], revision=config["revision"],
                        local_weights_dir=str(args.weights.resolve()))
        model_files = {name: {"bytes": (args.weights / name).stat().st_size,
                              "sha256": sha256(args.weights / name)} for name in MODEL_FILES}
        if model_files != config["model_files"]:
            raise ValueError("one or more of the eight original pinned model files differ")
        manifest["model_files"] = model_files
        save(args.output / "manifest-start.json", manifest)
        import numpy as np
        import torch
        import transformers
        from transformers import AutoModelForCausalLM, AutoTokenizer, DynamicCache, cache_utils
        from transformers.models.qwen3 import modeling_qwen3

        if torch.__version__ != config["torch_version"] or transformers.__version__ != config["transformers_version"]:
            raise ValueError("package versions differ from the frozen experiment")
        implementations = {name: {"path": inspect.getfile(module), "sha256": sha256(inspect.getfile(module))}
                           for name, module in (("qwen3", modeling_qwen3), ("cache", cache_utils))}
        if any(implementations[name]["sha256"] != expected for name, expected in IMPLEMENTATION_SHA256.items()):
            raise ValueError("reviewed installed Qwen3/cache source hash mismatch")
        manifest["implementation_files"] = implementations
        manifest["packages"] = {name: importlib.metadata.version(name) for name in (
            "torch", "transformers", "numpy", "safetensors", "tokenizers", "huggingface-hub")}
        torch.set_num_threads(4)
        torch.set_num_interop_threads(1)
        torch.manual_seed(20261022)
        torch.use_deterministic_algorithms(True)
        manifest["runtime"] = {"threads": torch.get_num_threads(), "interop_threads": torch.get_num_interop_threads(),
                               "dtype": "float32", "device": "cpu", "attention": "eager",
                               "deterministic_algorithms": True, "torch_config": torch.__config__.show()}
        tokenizer = AutoTokenizer.from_pretrained(args.weights, local_files_only=True, trust_remote_code=False)
        ids = tokenizer(config["input_text"], add_special_tokens=False, return_tensors="pt")["input_ids"][:, :48].contiguous()
        if list(ids.shape) != [1, 48]:
            raise ValueError("frozen text has fewer than 48 tokens")
        save(args.output / "inputs.json", {"text": config["input_text"], "add_special_tokens": False,
             "token_ids": ids.tolist(), "token_bytes_sha256": hashlib.sha256(ids.numpy().tobytes()).hexdigest(),
             "teacher_forced": True, "generation": False, "prefix": 32, "steps": 16})
        model = AutoModelForCausalLM.from_pretrained(args.weights, local_files_only=True, trust_remote_code=False,
                    use_safetensors=True, dtype=torch.float32, attn_implementation="eager").to("cpu").eval()
        dimensions = {"hidden_size": 1024, "intermediate_size": 3072, "num_hidden_layers": 28,
                      "num_attention_heads": 16, "num_key_value_heads": 8, "head_dim": 128}
        if any(getattr(model.config, key) != value for key, value in dimensions.items()):
            raise ValueError("model dimensions differ from the frozen configuration")
        if model.config._attn_implementation != "eager" or any(t != "full_attention" for t in model.config.layer_types):
            raise ValueError("expected eager full attention")
        if any(p.dtype != torch.float32 or p.device.type != "cpu" for p in model.parameters()):
            raise ValueError("model is not CPU FP32")
        if any(getattr(module, name, {}) for module in model.modules()
               for name in ("_forward_hooks", "_forward_pre_hooks")):
            raise ValueError("model has unexpected pre-existing hooks")
        manifest["dimensions"] = dimensions
        manifest["selection"] = {"layer": 0, "query_head": 0, "kv_head": 0, "GQA_Q_heads_per_KV_head": 2,
                                 "source_boundary": "post q/k_norm and RoPE; actual full cache K/V; original eager output before o_proj"}
        cache, captures, call_state = DynamicCache(config=model.config), {}, {}
        original_eager = modeling_qwen3.eager_attention_forward
        with torch.inference_mode(), torch.autocast(device_type="cpu", enabled=False):
            with capture_eager(modeling_qwen3, call_state, captures):
                cursor = 0
                for end in [32] + list(range(33, 49)):
                    call_state["name"] = "prefill32" if end == 32 else ("decode48" if end == 48 else None)
                    positions = torch.arange(cursor, end, dtype=torch.long)
                    model(input_ids=ids[:, cursor:end], past_key_values=cache, use_cache=True,
                          attention_mask=torch.ones((1, end), dtype=torch.long),
                          position_ids=positions.unsqueeze(0), cache_position=positions, logits_to_keep=1)
                    cursor = end
        manifest["eager_callable_restored"] = modeling_qwen3.eager_attention_forward is original_eager
        if set(captures) != {"prefill32", "decode48"} or not manifest["eager_callable_restored"]:
            raise ValueError("missing capture or eager callable was not restored")
        summary = evaluate(captures, args.output)
        source_unchanged = (all(sha256(path) == expected for path, expected in source_files.items())
                            and git(source_root, "rev-parse", "HEAD") == source_commit)
        clean_end = not bool(git(source_root, "status", "--porcelain"))
        manifest["source_unchanged_at_end"] = source_unchanged
        manifest["source_clean_at_end"] = clean_end
        manifest["model_files_unchanged_at_end"] = all(
            sha256(args.weights / name) == record["sha256"] for name, record in model_files.items())
        manifest["status"] = "PASS" if (summary["status"] == "PASS" and source_unchanged
            and (args.development or clean_end) and manifest["model_files_unchanged_at_end"]) else "FAIL"
    except Exception as exc:
        save(args.output / "failure.json", {"status": "ERROR", "type": type(exc).__name__,
                                            "message": str(exc), "traceback": traceback.format_exc()})
        manifest["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        if original_eager is not None:
            from transformers.models.qwen3 import modeling_qwen3
            manifest["eager_callable_restored"] = modeling_qwen3.eager_attention_forward is original_eager
        manifest["finished_utc_epoch"] = time.time()
        manifest["artifacts"] = {p.name: {"bytes": p.stat().st_size, "sha256": sha256(p)}
            for p in sorted(args.output.iterdir()) if p.is_file() and p.name != "manifest.json"}
        save(args.output / "manifest.json", manifest)
    return manifest["status"]


if __name__ == "__main__":
    raise SystemExit(0 if main() == "PASS" else 1)
