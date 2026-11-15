"""Verify the archived FP32 seed and describe all state tensors for the replay ABI."""
import argparse
from collections import deque
import hashlib
import json
from pathlib import Path

import torch


def describe(reference):
    meta = json.loads((reference / "reference.json").read_text())
    seed = reference / "history512.pt"
    with seed.open("rb") as f:
        digest = hashlib.file_digest(f, "sha256").hexdigest()
    if meta["outputs"].get(seed.name) != digest:
        raise ValueError("reference cache SHA-256 mismatch")
    if meta.get("history_payload", "live FP32") != "live FP32":
        raise ValueError("expected a representative FP32 history")
    cache = torch.load(seed, weights_only=False, map_location="cpu")
    if cache.get_seq_length() != 512:
        raise ValueError("FP32 reference does not contain 512 positions")
    layers = []
    for i, layer in enumerate(cache.layers):
        state = {}
        for name in ("keys", "values", "conv_states", "recurrent_states"):
            item = getattr(layer, name, None)
            if item is None:
                continue
            if isinstance(item, dict):
                if set(item) != {0}:
                    raise ValueError(f"unexpected cache slots for {name} in layer {i}")
                item = item[0]
            items = (item,) if isinstance(item, torch.Tensor) else item
            if not isinstance(items, (list, tuple, deque)):
                raise ValueError(f"unexpected {type(items).__name__} storage for {name} in layer {i}")
            tensors = []
            for x in items:
                if not isinstance(x, torch.Tensor) or not torch.isfinite(x).all():
                    raise ValueError(f"invalid {name} tensor in layer {i}")
                tensors.append({
                    "shape": list(x.shape),
                    "dtype": str(x.dtype),
                    "max_abs": float(x.abs().max()),
                    "nonzero": int(torch.count_nonzero(x)),
                })
            state[name] = tensors
        if not state:
            raise ValueError(f"no recognized cache state in layer {i}")
        layers.append({"index": i, "class": type(layer).__name__, "states": state})
    if not any(x["nonzero"] for layer in layers for entries in layer["states"].values() for x in entries):
        raise ValueError("archived cache has no nonzero state")
    return {"model": meta["model"], "reference_sha256": digest,
            "seed_token": meta["decode"][0]["input"], "position": 512, "layers": layers}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reference", type=Path)
    args = parser.parse_args()
    torch.set_num_threads(2)
    print(json.dumps(describe(args.reference), indent=2))
