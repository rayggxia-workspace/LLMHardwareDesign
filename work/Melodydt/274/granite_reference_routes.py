"""Trace selected Granite experts and layer residuals for the zero-history audit."""
import argparse
import json
from pathlib import Path

import torch
from transformers import AutoModelForCausalLM

from reference_workload import sha


def main(reference, candidate, output, threads):
    torch.set_num_threads(threads)
    torch.set_num_interop_threads(1)
    receipt = json.loads((reference / "reference.json").read_text())
    replay = json.loads((candidate / "result.json").read_text())
    model = AutoModelForCausalLM.from_pretrained(
        receipt["checkpoint"], local_files_only=True, trust_remote_code=False,
        dtype=torch.float32, attn_implementation="eager",
    ).eval()
    past = torch.load(reference / "history512.pt", weights_only=False)
    if any(torch.count_nonzero(t).item() for layer in past.layers for t in (layer.keys, layer.values)):
        raise ValueError("history tensors are not zero")
    routes = {}
    residual = {}

    def capture_route(index):
        def hook(_module, _inputs, result):
            routes[index] = result[0].flatten().tolist()
        return hook

    def capture_residual(index):
        def hook(_module, _inputs, result):
            residual[index] = result.detach().flatten().clone()
        return hook

    for i, layer in enumerate(model.model.layers):
        layer.block_sparse_moe.router.register_forward_hook(capture_route(i))
        layer.register_forward_hook(capture_residual(i))
    layers = len(model.model.layers)
    summary = []
    output.mkdir()
    with torch.inference_mode():
        for step, retire in enumerate(replay["retirements"]):
            token = torch.tensor([[retire["input"]]], dtype=torch.long)
            result = model(input_ids=token, past_key_values=past, use_cache=True, logits_to_keep=1)
            past = result.past_key_values
            reference_logits = torch.load(reference / f"decode-{step}-logits.pt", weights_only=True)
            if not torch.equal(result.logits[:, -1], reference_logits):
                raise ValueError(f"reference logits did not reproduce in step {step}")
            details = []
            for layer in range(layers):
                observed = replay["expert_routes"][step*layers+layer]["ids"]
                expected = routes[layer]
                details.append({"layer": layer, "fp32": expected, "candidate": observed,
                                "common": len(set(expected).intersection(observed)),
                                "fp32_residual_abs_max": float(residual[layer].abs().max())})
            path = output / f"fp32-residual-{step}.pt"
            torch.save(torch.stack([residual[i] for i in range(layers)]), path)
            summary.append({"input": retire["input"], "fp32_top1": int(reference_logits.argmax()),
                            "candidate_top1": retire["selected"], "routes": details,
                            "reference_residual_sha256": sha(path)})
    (output / "comparison.json").write_text(json.dumps({
        "reference_sha256": sha(reference / "reference.json"),
        "candidate_result_sha256": sha(candidate / "result.json"),
        "steps": summary,
    }, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reference", type=Path)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("threads", type=int)
    main(**vars(parser.parse_args()))
