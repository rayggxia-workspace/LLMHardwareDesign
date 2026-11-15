"""Compare a replay's second step with FP32 on the same feedback token."""
import argparse
import json
from pathlib import Path

import torch
from transformers import AutoModelForCausalLM

from reference_workload import sha


def main(reference, candidate, output, threads):
    torch.set_num_threads(threads)
    torch.set_num_interop_threads(1)
    ref = json.loads((reference / "reference.json").read_text())
    first = json.loads((candidate / "progress.json").read_text())["retirements"][0]
    if ref["history_payload"] != "zeros" or first["input"] != ref["decode"][0]["input"]:
        raise ValueError("incompatible initial state or input token")
    model = AutoModelForCausalLM.from_pretrained(
        ref["checkpoint"], local_files_only=True, trust_remote_code=False,
        dtype=torch.float32, attn_implementation="eager",
    ).eval()
    previous = torch.load(reference / "history512.pt", weights_only=False)
    token = torch.tensor([[first["input"]]])
    forced = torch.tensor([[first["selected"]]])
    with torch.inference_mode():
        a = model(input_ids=token, past_key_values=previous, use_cache=True, logits_to_keep=1)
        original = torch.load(reference / "decode-0-logits.pt", weights_only=True)
        torch.testing.assert_close(a.logits[:, -1], original, rtol=1e-6, atol=1e-6)
        b = model(input_ids=forced, past_key_values=a.past_key_values, use_cache=True, logits_to_keep=1)
        vectors = b.logits[:, -1].contiguous()
        if not torch.isfinite(vectors).all() or b.past_key_values.get_seq_length() != 514:
            raise ValueError("invalid matched-input FP32 decode output")
    output.mkdir()
    payload = output / "decode-1-aligned-logits.pt"
    torch.save(vectors, payload)
    (output / "comparison-input.json").write_text(json.dumps({
        "reference_sha256": sha(reference / "reference.json"),
        "candidate_first_input": first["input"],
        "candidate_first_logits_sha256": first["logits_sha256"],
        "second_token": int(forced.item()),
        "fp32_selected": int(vectors.argmax()),
        "fp32_logits_sha256": sha(payload),
    }, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reference", type=Path)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("threads", type=int)
    main(**vars(parser.parse_args()))
