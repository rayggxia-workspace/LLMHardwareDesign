"""Bind an independently saved FP32 prefix to the short replay's DDR layout."""
from collections import deque
from hashlib import file_digest, sha256
import json
from pathlib import Path

import numpy as np


def encode_q16(x, label):
    scaled = np.rint(x.astype(np.float64) * 65536)
    if not np.isfinite(scaled).all() or np.any((scaled < -(1 << 31)) | (scaled >= 1 << 31)):
        raise ValueError(f"{label} cannot be represented in S32/Q16 without saturation")
    return scaled.astype("<i4").tobytes()


def _one_state(layer, name):
    state = getattr(layer, name)
    if isinstance(state, dict):
        if set(state) != {0}:
            raise ValueError(f"unexpected cache slots for {name}")
        state = state[0]
    if isinstance(state, (tuple, list, deque)):
        state, = state
    return state.detach().cpu().float().numpy()


def materialize(reference, compiler, plan, model, assets):
    import torch

    payload = reference / "history512.pt"
    receipt_file = reference / "reference.json"
    receipt = json.loads(receipt_file.read_text())
    if (plan["history"], plan["first_decode_input"], receipt["model"]) != (
            512, receipt["decode"][0]["input"], model):
        raise ValueError("history receipt differs from workload")
    with payload.open("rb") as f:
        digest = file_digest(f, "sha256").hexdigest()
    if (digest != receipt["outputs"][payload.name] or
            receipt.get("history_payload", "live FP32") != "live FP32"):
        raise ValueError("expected the frozen nonzero FP32 history")
    cache = torch.load(payload, map_location="cpu", weights_only=False)
    if int(cache.get_seq_length()) != plan["history"] or len(cache.layers) != plan["layers"]:
        raise ValueError("reference cache shape differs from replay")
    store = assets / "representative-history"
    store.mkdir()
    regions = []
    nonzero = 0

    def write(address, packed, label):
        nonlocal nonzero
        if address % 64 or len(packed) % 64:
            raise ValueError("unaligned representative history image")
        file = store / (label + ".bin")
        file.write_bytes(packed)
        nonzero += int(np.count_nonzero(np.frombuffer(packed, dtype="<i4")))
        regions.append({"address": address, "bytes": len(packed),
                        "file": str(file.relative_to(assets)),
                        "sha256": sha256(packed).hexdigest()})

    kv_regions = []
    recurrent_regions = iter(plan.get("initial", []))
    row = plan["kv_row"]
    for i, layer in enumerate(cache.layers):
        if compiler.has_kv(i):
            for kind, name in enumerate(("keys", "values")):
                tensor = _one_state(layer, name)
                dim = getattr(compiler, "head_size", 128)
                if tensor.shape != (1, compiler.kv_heads, plan["history"], dim) or dim > row//4:
                    raise ValueError(f"unexpected {name} geometry in layer {i}: {tensor.shape}")
                for head, values in enumerate(tensor[0]):
                    if dim < row//4:
                        values = np.pad(values, ((0, 0), (0, row//4-dim)))
                    base = compiler.kv(i, head, kind)
                    kv_regions.append((base + plan["history"]*row, 2*row))
                    write(base, encode_q16(values, f"layer {i} {name}"),
                          f"layer-{i}-{name}-{head}")
        if model == "falcon" or model == "qwen35" and not compiler.has_kv(i):
            depth, channels = (128, 8192) if model == "qwen35" else (256, 4608)
            state = _one_state(layer, "recurrent_states")
            conv = _one_state(layer, "conv_states")
            if state.shape != (1, 32, 128, depth) or conv.shape != (1, channels, 4):
                raise ValueError(f"unexpected recurrent geometry in layer {i}: {state.shape}, {conv.shape}")
            if model == "qwen35":
                state = state.swapaxes(-1, -2)
            base, expected = next(recurrent_regions)
            packed = encode_q16(state, f"layer {i} recurrent state") + encode_q16(conv, f"layer {i} convolution state")
            if len(packed) != expected:
                raise ValueError("recurrent image and address span differ")
            write(base, packed, f"layer-{i}-recurrent")
    if set(kv_regions) != {tuple(item) for item in plan["state"]} or next(recurrent_regions, None) is not None:
        raise ValueError("reference cache does not cover the complete plan")
    if not nonzero:
        raise ValueError("representative history contains no nonzero Q16 values")
    return {"reference_sha256": sha256(receipt_file.read_bytes()).hexdigest(),
            "source_sha256": digest, "nonzero_values": nonzero, "images": regions}


def map_images(assets, manifest, expected):
    images = {}
    for image in manifest["images"]:
        address = image["address"]
        data = (assets / image["file"]).read_bytes()
        if (address in images or expected.get(address) != len(data) or
                image["bytes"] != len(data) or sha256(data).hexdigest() != image["sha256"]):
            raise ValueError("representative DDR image failed size, coverage or SHA-256 validation")
        images[address] = data
    if set(images) != set(expected):
        raise ValueError("missing representative DDR image")
    return images
