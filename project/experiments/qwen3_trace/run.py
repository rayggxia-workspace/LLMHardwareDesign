"""Run a pinned real-weight CPU experiment from a clean, recorded commit."""
import argparse
import gzip
import hashlib
import importlib.metadata
import inspect
import json
from pathlib import Path
import platform
import subprocess
import sys
import time
import traceback


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
MODEL_FILES = ("config.json", "generation_config.json", "tokenizer.json",
               "tokenizer_config.json", "merges.txt", "vocab.json", "LICENSE",
               "model.safetensors")


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def save(path, value):
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
                          encoding="utf-8")


def git(*arguments):
    return subprocess.check_output(["git", *arguments], cwd=ROOT, text=True).strip()


def source_snapshot():
    return {str(path.relative_to(ROOT)).replace("\\", "/"): sha256(path)
            for path in sorted(HERE.rglob("*"))
            if path.is_file() and "__pycache__" not in path.parts and "results" not in path.parts}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise ValueError("refusing to replace an existing output directory")
    if git("status", "--porcelain"):
        raise ValueError("formal run requires a clean worktree")
    config = json.loads((HERE / "experiment.json").read_text(encoding="utf-8"))
    source_commit, initial_source = git("rev-parse", "HEAD"), source_snapshot()
    model_files = {}
    for filename in MODEL_FILES:
        path = args.model_dir / filename
        model_files[filename] = {"bytes": path.stat().st_size, "sha256": sha256(path)}
    if model_files != config["model_files"]:
        raise ValueError("model/config/tokenizer files differ from the fixed revision")
    if model_files["model.safetensors"] != {
        "bytes": config["weights_bytes"], "sha256": config["weights_sha256"]
    }:
        raise ValueError("local weights do not match the fixed official artifact")
    args.out.mkdir(parents=True)
    started = time.time()
    manifest = {"schema_version": 1, "source_commit": source_commit,
                "source_dirty_at_start": False, "source_files": initial_source,
                "model_id": config["model_id"], "revision": config["revision"],
                "local_model_dir": str(args.model_dir.resolve()), "model_files": model_files,
                "python": sys.version, "platform": platform.platform(),
                "command": sys.argv, "started_utc_epoch": started,
                "scope": config["scope"]}
    save(args.out / "manifest-start.json", manifest)
    try:
        import torch
        import transformers
        from transformers import AutoModelForCausalLM, AutoTokenizer
        from transformers.models.qwen3 import modeling_qwen3
        from transformers import cache_utils
        from numeric import run_numeric
        from trace import run_trace

        if torch.__version__ != config["torch_version"] or transformers.__version__ != config["transformers_version"]:
            raise ValueError("environment differs from predeclared versions")
        manifest["packages"] = {name: importlib.metadata.version(name) for name in (
            "torch", "transformers", "safetensors", "tokenizers", "huggingface-hub", "numpy")}
        manifest["implementation_files"] = {
            name: {"path": inspect.getfile(module), "sha256": sha256(inspect.getfile(module))}
            for name, module in (("qwen3", modeling_qwen3), ("cache", cache_utils))}
        expected_implementation = {
            "qwen3": "4b95c371fd26d40c69083dab36ac1eafd8cf82b415a0bb827275097c5ad2305b",
            "cache": "f4e11caf14c75bdefa5e3003b93ef0e8b97fb6103375705ad944b0b344d7da8a",
        }
        for name, expected in expected_implementation.items():
            if manifest["implementation_files"][name]["sha256"] != expected:
                raise ValueError(f"installed {name} source differs from reviewed v4.57.6")
        torch.set_num_threads(config["threads"])
        torch.set_num_interop_threads(1)
        torch.manual_seed(20261022)
        torch.use_deterministic_algorithms(True)
        manifest["runtime"] = {"threads": torch.get_num_threads(),
                               "interop_threads": torch.get_num_interop_threads(),
                               "torch_config": torch.__config__.show(),
                               "deterministic_algorithms": True,
                               "device": "cpu", "dtype": "float32", "attention": "eager"}
        tokenizer = AutoTokenizer.from_pretrained(args.model_dir, local_files_only=True,
                                                  trust_remote_code=False)
        encoded = tokenizer(config["input_text"], add_special_tokens=False, return_tensors="pt")["input_ids"]
        total = max(case["prefix"] + case["steps"] for case in config["cases"])
        if encoded.shape[1] < total:
            raise ValueError("frozen text does not provide enough tokens")
        ids = encoded[:, :total].contiguous()
        save(args.out / "inputs.json", {"text": config["input_text"],
             "add_special_tokens": False, "token_ids": ids.tolist(),
             "token_bytes_sha256": hashlib.sha256(ids.numpy().tobytes()).hexdigest(),
             "teacher_forced": True, "generation": False})
        load_start = time.perf_counter()
        model = AutoModelForCausalLM.from_pretrained(
            args.model_dir, local_files_only=True, trust_remote_code=False,
            use_safetensors=True, dtype=torch.float32, attn_implementation="eager")
        model.to("cpu").eval()
        manifest["load_wall_seconds"] = time.perf_counter() - load_start
        actual_config = model.config.to_dict()
        expected_dims = {"hidden_size": 1024, "intermediate_size": 3072, "num_hidden_layers": 28,
                         "num_attention_heads": 16, "num_key_value_heads": 8, "head_dim": 128}
        if any(actual_config.get(k) != value for k, value in expected_dims.items()):
            raise ValueError("loaded architecture differs from the frozen observation contract")
        if (model.config._attn_implementation != "eager"
                or any(t != "full_attention" for t in model.config.layer_types)):
            raise ValueError("observation contract requires eager full-attention layers")
        if any(parameter.dtype != torch.float32 or parameter.device.type != "cpu"
               for parameter in model.parameters()):
            raise ValueError("model dtype/device mismatch")
        manifest["model"] = {"independent_parameter_elements": sum(p.numel() for p in model.parameters()),
                             "state_dict_elements": sum(t.numel() for t in model.state_dict().values()),
                             "embedding_lm_head_share_storage": (
                                 model.model.embed_tokens.weight.data_ptr() == model.lm_head.weight.data_ptr()),
                             "config": actual_config}
        cases = []
        with torch.inference_mode():
            for case in config["cases"]:
                begin = time.perf_counter()
                result = run_numeric(model, ids, prefix=case["prefix"], steps=case["steps"],
                                     atol=config["atol"], rtol=config["rtol"])
                save(args.out / f"{case['name']}-numeric.json", result)
                if result["status"] not in ("PASS", "FAIL"):
                    raise ValueError("numeric result schema has an unknown status")
                trace_result = None
                if case["trace"]:
                    trace_result = run_trace(model, ids, case["prefix"], case["steps"],
                                             config["selected_layers"], config["atol"], config["rtol"])
                    events = trace_result.pop("events")
                    serialized = b"".join((json.dumps(e, separators=(",", ":")) + "\n").encode()
                                          for e in events)
                    (args.out / f"{case['name']}-events.jsonl.gz").write_bytes(gzip.compress(serialized, mtime=0))
                    trace_result["event_count"] = len(events)
                    save(args.out / f"{case['name']}-trace.json", trace_result)
                cases.append({**case, "numeric_status": result["status"],
                              "trace_status": trace_result["status"] if trace_result else "not_requested",
                              "wall_seconds": time.perf_counter() - begin})
                save(args.out / "cases-progress.json", cases)
        unchanged = (source_snapshot() == initial_source and not git("status", "--porcelain")
                     and git("rev-parse", "HEAD") == source_commit)
        manifest["source_unchanged_at_end"] = unchanged
        data_unchanged = all(sha256(args.model_dir / name) == record["sha256"]
                             for name, record in model_files.items())
        manifest["model_files_unchanged_at_end"] = data_unchanged
        status = "PASS" if unchanged and data_unchanged and all(
            case["numeric_status"] == "PASS" and case["trace_status"] in ("PASS", "not_requested")
            for case in cases) else "FAIL"
        save(args.out / "summary.json", {"status": status, "cases": cases,
             "scope": config["scope"], "wall_seconds": time.time() - started})
    except Exception as error:
        save(args.out / "failure.json", {"status": "ERROR", "type": type(error).__name__,
             "message": str(error), "traceback": traceback.format_exc()})
        manifest["status"] = "ERROR"
        raise
    finally:
        manifest["finished_utc_epoch"] = time.time()
        manifest["artifacts"] = {p.name: sha256(p) for p in sorted(args.out.iterdir())
                                  if p.is_file() and p.name != "manifest.json"}
        save(args.out / "manifest.json", manifest)
    return status


if __name__ == "__main__":
    raise SystemExit(0 if main() == "PASS" else 1)
