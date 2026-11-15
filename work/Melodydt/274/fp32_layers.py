"""Capture FP32 decoder-layer output at the same token and cache boundaries as a replay."""
import argparse
import hashlib
import json
from pathlib import Path

import torch
from transformers import AutoModelForCausalLM

from reference_workload import sha


def trace(reference, out, threads):
    torch.set_num_threads(threads)
    torch.set_num_interop_threads(1)
    source = reference / "reference.json"
    receipt = json.loads(source.read_text())
    seed = reference / "history512.pt"
    ids = reference / "input-ids.json"
    if receipt.get("history_payload", "live FP32") != "live FP32":
        raise ValueError("expected representative FP32 history")
    for path in (seed, ids):
        if sha(path) != receipt["outputs"][path.name]:
            raise ValueError(f"reference input SHA-256 differs: {path.name}")
    model = AutoModelForCausalLM.from_pretrained(
        receipt["checkpoint"], local_files_only=True, trust_remote_code=False,
        dtype=torch.float32, attn_implementation="eager",
    ).eval()
    decoder, = [module for name, module in model.named_modules()
                if name.endswith(".layers") and isinstance(module, torch.nn.ModuleList)
                and len(module) == len(receipt["initial_state"]["layers"])]
    out.mkdir()
    frames = []
    phase, step = "", 0

    def capture(index):
        def hook(module, inputs, output):
            hidden = output if isinstance(output, torch.Tensor) else output[0]
            if hidden.ndim != 3 or hidden.shape[0] != 1 or not torch.isfinite(hidden).all():
                raise ValueError("invalid layer hidden state")
            for offset, values in enumerate(hidden[0]):
                name = f"{phase}-{step+offset}-layer-{index}.f32"
                data = values.detach().cpu().contiguous().numpy().astype("<f4").tobytes()
                (out / name).write_bytes(data)
                frames.append({"file": name, "sha256": hashlib.sha256(data).hexdigest()})
        return hook

    for index, layer in enumerate(decoder):
        layer.register_forward_hook(capture(index))
    with torch.inference_mode():
        phase = "prefill"
        prompt = torch.tensor([json.loads(ids.read_text())[:2]])
        model(input_ids=prompt, use_cache=True, logits_to_keep=1)
        phase = "decode"
        cache = torch.load(seed, weights_only=False, map_location="cpu")
        for step, expected in enumerate(receipt["decode"]):
            result = model(input_ids=torch.tensor([[expected["input"]]]), past_key_values=cache,
                           use_cache=True, logits_to_keep=1)
            cache = result.past_key_values
            golden = torch.load(reference / f"decode-{step}-logits.pt", weights_only=True)
            torch.testing.assert_close(result.logits[:, -1], golden, rtol=1e-6, atol=1e-6)
    if len(frames) != 4*len(decoder):
        raise ValueError("missing layer captures")
    (out / "trace.json").write_text(json.dumps({"model": receipt["model"], "reference_sha256": sha(source),
                                              "history_source_sha256": receipt["outputs"][seed.name],
                                              "frames": frames}, indent=2)+"\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reference", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("threads", type=int)
    args = parser.parse_args()
    trace(args.reference, args.output, args.threads)
