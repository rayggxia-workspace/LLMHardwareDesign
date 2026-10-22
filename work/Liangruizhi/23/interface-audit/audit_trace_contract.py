"""Pure stdlib protocol checks only: no torch import, no model execution."""
import ast
import copy
import hashlib
import json
import math
from pathlib import Path
from types import SimpleNamespace

ROOT = Path("D:/Projects/LLMHardwareDesign-inference/project/experiments/qwen3_trace")
OUT = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    source = (ROOT / "trace.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    function = next(node for node in tree.body if isinstance(node, ast.FunctionDef)
                    and node.name == "audit_events")
    isolated = ast.Module(body=[function], type_ignores=[])
    namespace = {}
    exec(compile(isolated, "reviewed-audit-events-only", "exec"), namespace)
    check = namespace["audit_events"]
    config = SimpleNamespace(hidden_size=1024, intermediate_size=3072,
        num_attention_heads=16, num_key_value_heads=8, head_dim=128,
        num_hidden_layers=28)

    def events(q, k):
        # Independently enumerated published Qwen3-0.6B boundary shapes.
        shapes = {
            "q_projection_pre_norm_rope": [1, q, 2048],
            "k_projection_pre_norm_rope": [1, q, 1024],
            "v_projection": [1, q, 1024],
            "attention_output": [1, q, 1024],
            "ffn_gate_projection": [1, q, 3072],
            "ffn_up_projection": [1, q, 3072],
            "ffn_output": [1, q, 1024],
            "decoder_output": [1, q, 1024],
            "swiglu_product_before_down_proj": [1, q, 3072],
            "attention.query_post_rope": [1, 16, q, 128],
            "attention.key_cached_post_rope": [1, 8, k, 128],
            "attention.value_cached": [1, 8, k, 128],
            "attention.context_before_o_proj": [1, q, 16, 128],
            "attention.probabilities": [1, 16, q, k],
        }
        return [dict(layer=layer, stage=stage, shape=shape.copy(),
                     dtype="torch.float32", itemsize=4, numel=math.prod(shape),
                     logical_bytes=math.prod(shape) * 4)
                for layer in range(28) for stage, shape in shapes.items()]

    results = []
    for q, k in ((32, 32), (16, 32), (1, 48)):
        valid = events(q, k)
        mutations = {"valid": valid,
            "missing_one_event": copy.deepcopy(valid[:-1]),
            "missing_entire_layer": [copy.deepcopy(e) for e in valid if e["layer"] != 13],
            "duplicate": copy.deepcopy(valid + valid[:1]),
            "wrong_gqa_heads_consistent_bytes": copy.deepcopy(valid),
            "raw_projection_shape_as_post_rope": copy.deepcopy(valid),
            "wrong_dtype_consistent_bytes": copy.deepcopy(valid),
            "wrong_logical_bytes": copy.deepcopy(valid),
            "unexpected_stage": copy.deepcopy(valid),
            "out_of_range_layer": copy.deepcopy(valid)}
        def find(name, stage):
            return next(e for e in mutations[name] if e["stage"] == stage)
        e = find("wrong_gqa_heads_consistent_bytes", "attention.key_cached_post_rope")
        e["shape"][1] = 16
        e["numel"] = math.prod(e["shape"])
        e["logical_bytes"] = e["numel"] * 4
        e = find("raw_projection_shape_as_post_rope", "attention.key_cached_post_rope")
        e["shape"] = [1, k, 1024]  # Same numel and bytes, wrong semantic axes.
        e = mutations["wrong_dtype_consistent_bytes"][0]
        e.update(dtype="torch.float16", itemsize=2, logical_bytes=e["numel"] * 2)
        mutations["wrong_logical_bytes"][0]["logical_bytes"] += 4
        mutations["unexpected_stage"][0]["stage"] = "unverified_label"
        mutations["out_of_range_layer"][0]["layer"] = 28
        for name, candidate in mutations.items():
            outcome = check(candidate, config, q, k)
            expected = name == "valid"
            results.append({"query_tokens": q, "total_tokens": k, "case": name,
                "events": len(candidate), "accepted": outcome["pass"],
                "expected_acceptance": expected,
                "pass": outcome["pass"] == expected,
                "failure_records": len(outcome["failures"])})

    config_json = json.loads((ROOT / "experiment.json").read_text(encoding="utf-8"))
    receipt_path = OUT.parent / "environment/receipts/model-download-manifest.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    frozen = {e["name"]: {"bytes": e["bytes"], "sha256": e["sha256"]}
              for e in receipt["files"]}
    binding = (frozen == config_json["model_files"]
               and receipt["revision"] == config_json["revision"]
               and receipt["model_id"] == config_json["model_id"]
               and all(e["revision"] == receipt["revision"] for e in receipt["files"]))
    result = {"scope": "Synthetic event-contract tests and frozen receipt consistency; no torch import, no model execution, no independent second download or weight rehash.",
        "source_files": {name: sha(ROOT / name) for name in
                         ("trace.py", "run.py", "experiment.json", "numeric.py")},
        "download_receipt_sha256": sha(receipt_path),
        "model_file_bindings": len(frozen), "model_receipt_binding_pass": binding,
        "checks": results, "positive_checks": 3, "negative_checks": 27,
        "status": "PASS" if binding and all(r["pass"] for r in results) else "FAIL"}
    path = OUT / "trace-contract-results.json"
    path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "positive_checks": 3,
                     "negative_checks": 27, "model_file_bindings": len(frozen),
                     "result_sha256": sha(path), "source_files": result["source_files"]}))


if __name__ == "__main__":
    main()
