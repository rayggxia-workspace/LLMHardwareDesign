"""Generate short-workload reference inputs from frozen real checkpoints."""
import argparse
import hashlib
import json
from pathlib import Path
import time

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def summarize_cache(cache):
    return {
        "format": type(cache).__name__,
        "length": int(cache.get_seq_length()),
        "layers": [type(layer).__name__ for layer in cache.layers],
    }


def data_path(archive, name):
    checkpoint = Path(json.loads(archive.read_text())["models"][name]["checkpoint"])
    receipt = json.loads((checkpoint / "export_receipt.json").read_text())
    return Path(receipt["model_path"]), sha(checkpoint / "export_receipt.json")


def run(model_path, label, out, threads, export_receipt=None):
    out.mkdir()
    torch.set_num_threads(threads)
    torch.set_num_interop_threads(1)
    model_files = [model_path / "config.json", *sorted(model_path.glob("*.safetensors"))]
    if len(model_files) < 2:
        raise ValueError("expected a complete local source checkpoint")
    tok = AutoTokenizer.from_pretrained(model_path, local_files_only=True, trust_remote_code=False)
    model = AutoModelForCausalLM.from_pretrained(
        model_path, local_files_only=True, trust_remote_code=False,
        dtype=torch.float32, attn_implementation="eager",
    ).eval()
    text = ("Hello world. This document records a deterministic reference workload. "
            "The next token depends on the text and the cache. ") * 100
    ids = tok(text, add_special_tokens=True, return_tensors="pt").input_ids[:, :512]
    if tuple(ids.shape) != (1, 512):
        raise ValueError("expected 512 valid input positions")
    begin = time.monotonic()
    with torch.inference_mode():
        short = model(input_ids=ids[:, :2], use_cache=True, output_hidden_states=True)
        if not torch.isfinite(short.logits).all():
            raise ValueError("non-finite short prefill logits")
        torch.save(short.hidden_states[-1][:, -1].contiguous(), out / "prefill-post-norm.pt")
        short_state = summarize_cache(short.past_key_values)
        del short
        prefix = model(input_ids=ids, use_cache=True, logits_to_keep=1)
        first = prefix.logits[:, -1].argmax(dim=-1, keepdim=True)
        past = prefix.past_key_values
        initial_state = summarize_cache(past)
        if initial_state["length"] != 512:
            raise ValueError("checkpoint cache did not cover 512 input positions")
        torch.save(past, out / "history512.pt")
        del prefix
        step_tokens = []
        current = first
        for step in range(2):
            current_id = int(current.item())
            result = model(input_ids=current, past_key_values=past, use_cache=True,
                           logits_to_keep=1)
            if not torch.isfinite(result.logits).all():
                raise ValueError("non-finite decode logits")
            current = result.logits[:, -1].argmax(dim=-1, keepdim=True)
            past = result.past_key_values
            state = summarize_cache(past)
            if state["length"] != 513 + step:
                raise ValueError("decode did not advance cache position")
            torch.save(result.logits[:, -1].contiguous(), out / ("decode-{}-logits.pt".format(step)))
            step_tokens.append({"input": current_id, "selected": int(current.item()), "state": state})
    (out / "input-ids.json").write_text(json.dumps(ids.flatten().tolist()) + "\n")
    receipt = {
        "scope": "independent FP32 model reference with live 512-position history; no TLM timing",
        "model": label, "checkpoint": str(model_path), "archived_export_receipt_sha256": export_receipt,
        "checkpoint_files": {p.name: {"bytes": p.stat().st_size, "sha256": sha(p)} for p in model_files},
        "torch": torch.__version__, "short_prefill": short_state, "initial_state": initial_state,
        "decode": step_tokens, "reference_wall_seconds": time.monotonic() - begin,
        "outputs": {p.name: sha(p) for p in out.iterdir() if p.is_file()},
    }
    (out / "reference.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(label, step_tokens[0]["selected"], step_tokens[1]["selected"], flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("model")
    parser.add_argument("output", type=Path)
    parser.add_argument("threads", type=int)
    parser.add_argument("--checkpoint", type=Path)
    args = parser.parse_args()
    if args.checkpoint:
        path, source = args.checkpoint, None
    else:
        path, source = data_path(args.archive, args.model)
    run(path, args.model, args.output, args.threads, source)
