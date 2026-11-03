"""Compare the pinned official Qwen3 layer 0 with independent C++ FP32 traces.

Run only in the authorized server numerical job. No model download, tokenization,
RTL simulation, whole-model inference, or trained-quality acceptance occurs here.
Both frozen error limits apply independently to every case/stage, without rtol.
"""
import argparse
import datetime
import hashlib
import inspect
import json
import math
import os
import platform
import re
import sys
from pathlib import Path


REVISION = "c1899de289a04d12100db370d81485cdf75e47ca"
MODEL_SOURCE_BLOB = "5fec83d47888e44a0f3e0ffb2b067ce08e4712d3"
ATOL = 5e-4
RELATIVE_L2_LIMIT = 5e-5
STAGES = (("Y", 1024), ("norm", 1024), ("gate", 3072),
          ("up", 3072), ("mid", 3072), ("down", 1024), ("Z", 1024))
CASES = (("cal_text_0", "cal", (9707, 1879, 0, 198)),
         ("cal_math_0", "cal", (16, 10, 16, 28)),
         ("eval_text_0", "eval", (785, 8251, 374, 2613)),
         ("eval_math_0", "eval", (17, 9, 18, 28)))
TENSORS = (
    ("input_layernorm.weight", "input_layernorm.weight", (1024,)),
    ("post_attention_layernorm.weight", "post_attention_layernorm.weight", (1024,)),
    ("self_attn.q_norm.weight", "self_attn.q_norm.weight", (128,)),
    ("self_attn.k_norm.weight", "self_attn.k_norm.weight", (128,)),
    ("self_attn.q_proj.weight", "self_attn.q_proj.weight", (2048, 1024)),
    ("self_attn.k_proj.weight", "self_attn.k_proj.weight", (1024, 1024)),
    ("self_attn.v_proj.weight", "self_attn.v_proj.weight", (1024, 1024)),
    ("self_attn.o_proj.weight", "self_attn.o_proj.weight", (1024, 2048)),
    ("mlp.gate_proj.weight", "mlp.gate_proj.weight", (3072, 1024)),
    ("mlp.up_proj.weight", "mlp.up_proj.weight", (3072, 1024)),
    ("mlp.down_proj.weight", "mlp.down_proj.weight", (1024, 3072)))


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def git_blob(raw):
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def write_json(path, value):
    path.write_bytes((json.dumps(value, ensure_ascii=False, indent=2,
                                allow_nan=False) + "\n").encode("utf-8"))


def within(root, relative):
    require(isinstance(relative, str) and relative and not Path(relative).is_absolute(),
            "expected a relative input path")
    path = (root / relative).resolve()
    require(root in path.parents, "input path escapes its declared root")
    require(path.is_file(), "missing input: " + relative)
    return path


def tracked_read(root, relative, label, inputs, expected_bytes=None, expected_sha=None):
    path = within(root, relative)
    raw = path.read_bytes()
    if expected_bytes is not None:
        require(len(raw) == expected_bytes, "input length mismatch: " + label)
    actual = digest(raw)
    if expected_sha is not None:
        require(actual == expected_sha, "input SHA mismatch: " + label)
    inputs.append({"label": label, "root": str(root), "path": relative,
                   "bytes": len(raw), "sha256": actual})
    return raw


def tensor_data(np, data, entry, shape, inputs):
    require(entry.get("shape") == list(shape) and entry.get("source_dtype") == "BF16",
            "tensor shape or source dtype differs")
    count = math.prod(shape)
    raw = {}
    for kind, width in (("bf16le", 2), ("f32le", 4)):
        require(entry[kind + "_bytes"] == count * width, "manifest tensor byte count")
        raw[kind] = tracked_read(data, entry[kind + "_file"], entry.get("name", "embedding") + ":" + kind,
                                 inputs, count * width, entry[kind + "_sha256"])
    b16 = np.frombuffer(raw["bf16le"], dtype="<u2")
    b32 = np.frombuffer(raw["f32le"], dtype="<u4")
    require(np.array_equal(b16.astype(np.uint32) << 16, b32), "BF16/F32 scalar bit mismatch")
    values = np.frombuffer(raw["f32le"], dtype="<f4").copy().reshape(shape)
    require(bool(np.isfinite(values).all()), "nonfinite source tensor")
    return values


def load_data(np, root, inputs):
    manifest_raw = tracked_read(root, "manifest.json", "dataset manifest", inputs)
    manifest = json.loads(manifest_raw.decode("utf-8"))
    require(manifest.get("status") == "COMPLETE_SELECTED_TENSORS_AND_ROWS", "incomplete dataset")
    require(manifest.get("repo") == "Qwen/Qwen3-0.6B" and manifest.get("revision") == REVISION,
            "unpinned model dataset")
    assets = {}
    for row in manifest["assets"]:
        require(row["file"] not in assets, "duplicate asset")
        raw = tracked_read(root, row["file"], "official asset", inputs, row["bytes"], row["sha256"])
        require(git_blob(raw) == row["official_git_blob_sha1"], "official asset Git blob mismatch")
        assets[row["file"]] = raw
    require(manifest["config_file"] in assets, "config absent from verified assets")
    config = json.loads(assets[manifest["config_file"]].decode("utf-8"))
    expected = {"hidden_size": 1024, "intermediate_size": 3072, "num_attention_heads": 16,
                "num_key_value_heads": 8, "head_dim": 128, "rms_norm_eps": 1e-6,
                "rope_theta": 1000000, "rope_scaling": None, "attention_bias": False,
                "attention_dropout": 0.0, "hidden_act": "silu", "use_sliding_window": False}
    require(all(config.get(k) == v for k, v in expected.items()), "config outside the frozen layer ABI")
    entries = {row["name"]: row for row in manifest["tensors"]}
    require(len(entries) == len(manifest["tensors"]) == 11, "expected exactly eleven unique layer tensors")
    expected_names = {"model.layers.0." + row[0] for row in TENSORS}
    require(set(entries) == expected_names, "unexpected or missing layer0 tensor")
    values = {}
    for suffix, state_key, shape in TENSORS:
        values[state_key] = tensor_data(np, root, entries["model.layers.0." + suffix], shape, inputs)
    embeddings = {}
    for row in manifest["embedding_rows"]:
        token = row["token_id"]
        require(type(token) is int and 0 <= token < 151936 and token not in embeddings,
                "duplicate or invalid embedding token")
        embeddings[token] = tensor_data(np, root, row, (1024,), inputs)
    cases_raw = tracked_read(root, manifest["token_sequences_file"], "token sequences", inputs)
    cases = json.loads(cases_raw.decode("utf-8"))["token_sequences"]
    actual = [(row["id"], row["split"], tuple(row["token_ids"])) for row in cases]
    require(actual == list(CASES), "this qualification is limited to the same four frozen prefixes")
    require(all(token in embeddings for _, _, ids in CASES for token in ids), "missing embedding row")
    return manifest, config, values, embeddings, cases


def load_cpp_index(root, inputs):
    raw = tracked_read(root, "fp32-stage-index.tsv", "C++ FP32 stage index", inputs)
    index = {}
    for line in raw.decode("utf-8").splitlines():
        fields = line.split("\t")
        require(len(fields) == 6, "C++ stage index must have six fields and no header")
        case, split, stage, rows, cols, filename = fields
        key = (case, stage)
        require(key not in index, "duplicate C++ case/stage")
        require(filename == "fp32/{}/{}.f32le".format(case, stage), "unexpected C++ stage path")
        index[key] = {"split": split, "rows": int(rows), "cols": int(cols), "file": filename}
    expected = {(name, stage) for name, _, _ in CASES for stage, _ in STAGES}
    require(set(index) == expected, "C++ stage index differs from four cases by seven stages")
    for name, split, ids in CASES:
        for stage, cols in STAGES:
            row = index[(name, stage)]
            require((row["split"], row["rows"], row["cols"]) == (split, len(ids), cols),
                    "C++ indexed stage shape/split mismatch")
    return index


def metrics(np, official, independent):
    require(official.shape == independent.shape, "comparison tensor shape mismatch")
    require(bool(np.isfinite(official).all() and np.isfinite(independent).all()),
            "nonfinite comparison tensor")
    # FP64 metrics avoid an extra FP32 reduction error in the acceptance gate.
    reference = official.astype(np.float64).reshape(-1)
    observed = independent.astype(np.float64).reshape(-1)
    error = observed - reference
    error2 = float(np.dot(error, error))
    reference2 = float(np.dot(reference, reference))
    observed2 = float(np.dot(observed, observed))
    max_abs = float(np.max(np.abs(error)))
    relative_l2 = math.sqrt(error2 / reference2) if reference2 else math.sqrt(error2)
    return {"elements": int(reference.size), "max_abs_error": max_abs,
            "RMSE": math.sqrt(error2 / reference.size), "relative_L2": relative_l2,
            "relative_L2_zero_reference_fallback": "absolute L2" if not reference2 else None,
            "cosine": float(np.dot(reference, observed) / math.sqrt(reference2 * observed2))
                      if reference2 and observed2 else None,
            "reference_max_abs": float(np.max(np.abs(reference))),
            "independent_max_abs": float(np.max(np.abs(observed))),
            "max_abs_pass": max_abs <= ATOL,
            "relative_L2_pass": relative_l2 <= RELATIVE_L2_LIMIT,
            "passed": max_abs <= ATOL and relative_l2 <= RELATIVE_L2_LIMIT}


def module_source(path):
    path = Path(path).resolve()
    raw = path.read_bytes()
    return {"file": str(path), "bytes": len(raw), "sha256": digest(raw),
            "git_blob_sha1": git_blob(raw)}


def compare(args, summary):
    import numpy as np
    import torch
    import transformers
    from transformers.models.qwen3.configuration_qwen3 import Qwen3Config
    from transformers.models.qwen3.modeling_qwen3 import Qwen3DecoderLayer, Qwen3RotaryEmbedding

    require(platform.python_version_tuple()[:2] == ("3", "10"), "requires the frozen server Python3.10")
    require(np.__version__ == "2.2.6", "requires numpy2.2.6")
    require(torch.__version__ == "2.6.0+cpu", "requires Torch2.6.0+cpu")
    require(transformers.__version__ == "4.51.0", "requires transformers4.51.0")
    torch.set_num_threads(args.threads)
    torch.set_num_interop_threads(1)
    torch.set_default_dtype(torch.float32)
    torch.set_float32_matmul_precision("highest")
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    torch.use_deterministic_algorithms(True)
    torch.manual_seed(0)
    source = module_source(inspect.getsourcefile(Qwen3DecoderLayer))
    require(source["git_blob_sha1"] == MODEL_SOURCE_BLOB, "installed Qwen3 source differs from pinned official source")
    config_source = module_source(inspect.getsourcefile(Qwen3Config))
    summary["environment"] = {"python": platform.python_version(), "numpy": np.__version__,
                              "torch": torch.__version__, "transformers": transformers.__version__,
                              "device": "cpu", "dtype": "float32", "threads": args.threads,
                              "interop_threads": torch.get_num_interop_threads(),
                              "torch_config": torch.__config__.show(), "TF32": False,
                              "torch_deterministic_algorithms": True,
                              "framework_CPU_FMA": "official default CPU kernels; no claim that BLAS FMA is disabled",
                              "independent_cpp_FMA": "bound by the C++ job compile receipt, not inferred here"}
    summary["official_model_source"] = source
    summary["official_config_source"] = config_source
    inputs = summary["inputs"]
    manifest, config_dict, values, embeddings, cases = load_data(np, args.data_dir, inputs)
    index = load_cpp_index(args.cpp_dir, inputs)
    config = Qwen3Config(**config_dict)
    config._attn_implementation = "eager"
    config.use_cache = False
    config.torch_dtype = torch.float32
    layer = Qwen3DecoderLayer(config, layer_idx=0).to(device="cpu", dtype=torch.float32)
    state = {key: torch.from_numpy(value.copy()) for key, value in values.items()}
    require(set(layer.state_dict()) == set(state) and len(state) == 11, "official state_dict ABI differs")
    result = layer.load_state_dict(state, strict=True)
    require(not result.missing_keys and not result.unexpected_keys, "strict weight load failed")
    layer.eval()
    rotary = Qwen3RotaryEmbedding(config, device="cpu").to(dtype=torch.float32).eval()
    require(all(p.device.type == "cpu" and p.dtype == torch.float32 for p in layer.parameters()),
            "non-FP32 or non-CPU official parameter")
    require(config._attn_implementation == "eager" and not layer.training, "unexpected attention mode")
    summary["model"] = {"repository": manifest["repo"], "revision": manifest["revision"],
                        "acquisition_source_commit": manifest["source_commit"],
                        "complete_model_file_sha_verified": manifest.get("full_file_sha256_verified", False),
                        "official_classes": ["Qwen3Config", "Qwen3DecoderLayer", "Qwen3RotaryEmbedding"],
                        "strict_state_dict_keys": sorted(state), "layer_index": 0,
                        "attention": "eager; explicit additive causal mask; batch1; no padding/cache; positions0..3",
                        "epsilon": config.rms_norm_eps, "rope_theta": config.rope_theta,
                        "integer_RTL_executed": False}
    captured = {}
    counts = {}

    def save(stage, tensor):
        require(stage not in captured, "official hook called more than once: " + stage)
        require(tensor.dtype == torch.float32 and tensor.device.type == "cpu", "hook dtype/device differs")
        captured[stage] = tensor.detach().clone().cpu().numpy().copy()
        counts[stage] = counts.get(stage, 0) + 1

    handles = [layer.post_attention_layernorm.register_forward_pre_hook(lambda mod, a: save("Y", a[0])),
               layer.post_attention_layernorm.register_forward_hook(lambda mod, a, o: save("norm", o)),
               layer.mlp.gate_proj.register_forward_hook(lambda mod, a, o: save("gate", o)),
               layer.mlp.up_proj.register_forward_hook(lambda mod, a, o: save("up", o)),
               layer.mlp.down_proj.register_forward_pre_hook(lambda mod, a: save("mid", a[0])),
               layer.mlp.down_proj.register_forward_hook(lambda mod, a, o: save("down", o))]
    try:
        for case in cases:
            name = case["id"]
            rows = len(case["token_ids"])
            captured.clear()
            counts.clear()
            x = torch.from_numpy(np.stack([embeddings[token] for token in case["token_ids"]])).unsqueeze(0)
            positions = torch.arange(rows, dtype=torch.long).unsqueeze(0)
            mask = torch.zeros((rows, rows), dtype=torch.float32)
            mask.masked_fill_(torch.triu(torch.ones((rows, rows), dtype=torch.bool), diagonal=1),
                              torch.finfo(torch.float32).min)
            with torch.inference_mode():
                position_embeddings = rotary(x, positions)
                result = layer(hidden_states=x, attention_mask=mask[None, None, :, :],
                               position_ids=positions, past_key_value=None, use_cache=False,
                               cache_position=positions[0], position_embeddings=position_embeddings,
                               output_attentions=True)
            require(isinstance(result, tuple) and len(result) == 2, "official decoder output ABI differs")
            save("Z", result[0])
            require(set(captured) == {s for s, _ in STAGES} and all(v == 1 for v in counts.values()),
                    "missing or duplicate official hooks")
            trace_dir = args.output_dir / "framework-traces" / name
            trace_dir.mkdir(parents=True)
            for stage, width in STAGES:
                official = captured[stage]
                require(official.shape == (1, rows, width), "official stage shape differs")
                official = official[0]
                cpp_row = index[(name, stage)]
                raw = tracked_read(args.cpp_dir, cpp_row["file"], "C++ " + name + "/" + stage,
                                   inputs, rows * width * 4)
                independent = np.frombuffer(raw, dtype="<f4").reshape(rows, width)
                output = np.asarray(official, dtype="<f4").tobytes(order="C")
                (trace_dir / (stage + ".f32le")).write_bytes(output)
                row = {"case": name, "split": case["split"], "stage": stage,
                       "rows": rows, "cols": width, "token_ids": case["token_ids"],
                       "official_trace": str((trace_dir / (stage + ".f32le")).relative_to(args.output_dir)),
                       "official_bytes": len(output), "official_sha256": digest(output),
                       "cpp_sha256": digest(raw), "metrics": metrics(np, official, independent)}
                summary["comparisons"].append(row)
            for stage, alias in (("Y", ".F_input.f32le"), ("Z", ".layer0_FP32_output.f32le")):
                alias_raw = tracked_read(args.cpp_dir, name + alias, "C++ retained alias", inputs,
                                         rows * 1024 * 4)
                require(digest(alias_raw) == next(row["cpp_sha256"] for row in summary["comparisons"]
                                                if row["case"] == name and row["stage"] == stage),
                        "C++ legacy alias differs from its stage trace")
    finally:
        for handle in handles:
            handle.remove()
    for row in inputs:
        raw = within(Path(row["root"]), row["path"]).read_bytes()
        require(len(raw) == row["bytes"] and digest(raw) == row["sha256"], "input changed during comparison")
    summary["input_SHA_reverified_after_comparison"] = True
    summary["comparison_count"] = len(summary["comparisons"])
    require(summary["comparison_count"] == 28, "incomplete comparison set")
    passed = all(row["metrics"]["passed"] for row in summary["comparisons"])
    summary["status"] = ("PASS_OFFICIAL_QWEN3_LAYER0_FP32_REFERENCE_NOT_MODEL_QUALITY" if passed
                         else "FAIL_FROZEN_OFFICIAL_FRAMEWORK_REFERENCE_TOLERANCES")
    summary["reference_qualification_passed"] = passed
    return 0 if passed else 2


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--cpp-dir", "--numeric-dir", dest="cpp_dir", type=Path, required=True)
    parser.add_argument("--output-dir", "--output", dest="output_dir", type=Path, required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--threads", type=int, default=8)
    args = parser.parse_args()
    if not re.fullmatch("[0-9a-f]{40}", args.source_commit):
        parser.error("source-commit must be the actual forty-hex source commit")
    if not 1 <= args.threads <= 8:
        parser.error("threads must be1..8 within the assigned Slurm resources")
    args.data_dir = args.data_dir.resolve()
    args.cpp_dir = args.cpp_dir.resolve()
    args.output_dir = args.output_dir.resolve()
    if args.output_dir.exists():
        parser.error("output directory must not already exist")
    if any(root == args.output_dir or root in args.output_dir.parents
           for root in (args.data_dir, args.cpp_dir)):
        parser.error("output must be outside both immutable input directories")
    # Set bounds before importing either numerical runtime, including NumPy BLAS.
    thread_env = {}
    for key in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS",
                "BLIS_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS"):
        os.environ[key] = str(args.threads)
        thread_env[key] = str(args.threads)
    for key, value in (("OMP_DYNAMIC", "FALSE"), ("HF_HUB_OFFLINE", "1"),
                       ("TRANSFORMERS_OFFLINE", "1"), ("TOKENIZERS_PARALLELISM", "false")):
        os.environ[key] = value
        thread_env[key] = value
    args.output_dir.mkdir(parents=True)
    summary = {"schema_version": 1, "status": "RUNNING_OFFICIAL_FRAMEWORK_REFERENCE",
               "started_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
               "source_commit": args.source_commit,
               "script_sha256": digest(Path(__file__).read_bytes()),
               "data_dir": str(args.data_dir), "cpp_dir": str(args.cpp_dir),
               "thread_and_offline_environment": thread_env,
               "frozen_tolerances": {"max_abs_error_at_most": ATOL,
                                     "relative_L2_at_most": RELATIVE_L2_LIMIT,
                                     "rule": "both limits separately, every case/stage, no tolerance adjustment"},
               "inputs": [], "comparisons": [], "reference_qualification_passed": False,
               "model_quality_accepted": False, "RTL_executed": False,
               "limits": ["four fixed four-token prefixes are not representative quality data",
                          "official FP32/eager layer0 only, not official BF16/SDPA/FlashAttention equivalence",
                          "independent FP32-reference qualification, not integer accuracy acceptance",
                          "no full model/logits/generation/cache/physical or generic L5 acceptance",
                          "partial tensor extraction does not verify the complete model file SHA"]}
    write_json(args.output_dir / "framework-summary.json", summary)
    code = 1
    try:
        code = compare(args, summary)
    except Exception as exc:
        summary["status"] = "FAIL_CLOSED_OFFICIAL_FRAMEWORK_REFERENCE"
        summary["failure"] = {"type": type(exc).__name__, "message": str(exc)}
    finally:
        summary["ended_utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        summary["exit_code"] = code
        write_json(args.output_dir / "framework-summary.json", summary)
    print(json.dumps({"status": summary["status"], "comparisons": len(summary["comparisons"]),
                      "reference_qualification_passed": summary["reference_qualification_passed"],
                      "model_quality_accepted": False}, ensure_ascii=False))
    return code


if __name__ == "__main__":
    sys.exit(main())
