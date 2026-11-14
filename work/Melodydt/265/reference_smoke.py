"""Exercise the frozen Qwen checkpoint and ONNX stack on the Slurm CPU node."""

import argparse
import hashlib
import json
from pathlib import Path
import sys

from preflight import MANIFEST, read_json, require, validate_manifest, verify_reference_files


def reference_smoke(args, frozen):
    import numpy as np
    import onnx
    import onnxruntime as ort
    import torch
    import transformers
    from transformers import AutoModelForCausalLM, AutoTokenizer

    checkpoint = args.checkpoint.resolve()
    reference = args.reference.resolve()
    graphs = args.graphs.resolve()
    verify_reference_files(frozen, checkpoint, reference, graphs)

    torch.set_num_threads(args.threads)
    torch.set_num_interop_threads(1)
    tokenizer = AutoTokenizer.from_pretrained(str(checkpoint), local_files_only=True,
                                             trust_remote_code=False)
    model = AutoModelForCausalLM.from_pretrained(
        str(checkpoint), local_files_only=True, trust_remote_code=False,
        use_safetensors=True, torch_dtype=torch.float32, attn_implementation="eager",
    ).eval()
    params = sum(param.numel() for param in model.parameters())
    expected = frozen["workload"]
    require(params == expected["parameters"]
            and model.config.num_hidden_layers == expected["layers"]
            and model.config.vocab_size == expected["vocab_size"],
            "loaded a different checkpoint shape")
    require(all(param.dtype == torch.float32 for param in model.parameters()),
            "reference model was not loaded as FP32")

    cases = []
    prefill_graph = graphs / "export-1/cached.onnx"
    graph_options = ort.SessionOptions()
    graph_options.intra_op_num_threads = args.threads
    graph_options.inter_op_num_threads = 1
    graph_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_DISABLE_ALL
    graph_engine = ort.InferenceSession(str(prefill_graph), sess_options=graph_options,
                                        providers=["CPUExecutionProvider"])
    parameters = {f"model.{name}": param.detach().numpy()
                  for name, param in model.named_parameters()}
    graph_inputs = [value.name for value in graph_engine.get_inputs() if value.name != "input_ids"]
    require(set(graph_inputs) <= parameters.keys(), "P512 ONNX has unbound weights")
    graph_weights = {name: parameters[name] for name in graph_inputs}
    with torch.inference_mode():
        for case_id in ("case-2", "case-3"):
            tokens = read_json(reference / case_id / "tokens.json")
            prompt = torch.tensor([tokens["prompt"]], dtype=torch.long)
            prefill = model(input_ids=prompt, use_cache=True, logits_to_keep=1)
            first = prefill.logits[:, -1, :].argmax(-1).view(1, 1)
            cached = model(input_ids=first, past_key_values=prefill.past_key_values,
                           use_cache=True, logits_to_keep=1).logits[:, -1, :]
            prefix = torch.cat((prompt, first), dim=1)
            full = model(input_ids=prefix, use_cache=False, logits_to_keep=1).logits[:, -1, :]
            torch.testing.assert_close(cached, full, atol=5e-4, rtol=5e-4)
            generated = [int(first.item()), int(cached.argmax(-1).item())]
            require(generated == tokens["generated"][:2]
                    and generated[1] == int(full.argmax(-1).item()),
                    f"{case_id}: disagrees with frozen oracle")
            onnx_logits, = graph_engine.run(["logits"],
                                            dict(graph_weights, input_ids=prompt.numpy()))
            hf_logits = prefill.logits.numpy()
            require(onnx_logits.shape == hf_logits.shape and np.isfinite(onnx_logits).all(),
                    f"{case_id}: invalid ONNX prefill logits")
            cases.append({"case": case_id, "prompt_tokens": prompt.shape[1],
                          "generated_tokens": generated, "cached_decode_steps": 1,
                          "cached_vs_full_maxabs": float((cached - full).abs().max().item()),
                          "onnx_prefill_top1_matches_hf": bool(
                              np.array_equal(onnx_logits.argmax(-1), hf_logits.argmax(-1))),
                          "onnx_prefill_maxabs_vs_hf": float(np.abs(onnx_logits - hf_logits).max())})

    graph_checks = []
    for name, digest in frozen["historical_inputs"]["onnx"].items():
        path = graphs / name
        graph = onnx.load_model(str(path), load_external_data=False)
        onnx.checker.check_model(graph)
        graph_checks.append({"path": name, "sha256": digest, "nodes": len(graph.graph.node)})
    return {
        "scope": "HF FP32 reference environment and ONNX parser smoke",
        "passed": True,
        "full_p512_d128_qualified": False,
        "device_timing_qualified": False,
        "python": sys.version.split()[0],
        "torch": torch.__version__,
        "transformers": transformers.__version__,
        "onnx": onnx.__version__,
        "onnxruntime": ort.__version__,
        "checkpoint_revision": expected["publisher_revision"],
        "checkpoint_files_verified": len(frozen["checkpoint"]),
        "checkpoint_directory": str(checkpoint),
        "manifest_sha256": hashlib.sha256(MANIFEST.read_bytes()).hexdigest(),
        "parameter_count": params,
        "tokenizer_length": len(tokenizer),
        "cases": cases,
        "onnx_checker": graph_checks,
        "onnxruntime_p512_prefill_executed": True,
        "onnx_equivalence_qualified": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkpoint", type=Path)
    parser.add_argument("reference", type=Path)
    parser.add_argument("graphs", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--threads", type=int, default=4)
    args = parser.parse_args()
    require(args.threads > 0, "positive CPU thread count required")
    frozen = read_json(MANIFEST)
    validate_manifest(frozen)
    require(not args.output.exists(), "receipt already exists")
    result = reference_smoke(args, frozen)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")
    print("PASS: frozen reference and ONNX runtime smoke")


if __name__ == "__main__":
    main()
