"""Extract two Qwen3.5 weight rows and encode the native P16 load stream."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import random
import struct

from compile_slice import K


def sha(data):
    return hashlib.sha256(data).hexdigest()


def extract(model, layer, op, first):
    index = json.loads((model / "model.safetensors.index.json").read_text())["weight_map"]
    name, = [n for n in index if n.endswith(f".layers.{layer}.mlp.{op}.weight")]
    file = model / index[name]
    with file.open("rb") as f:
        length, = struct.unpack("<Q", f.read(8))
        entry = json.loads(f.read(length))[name]
        rows, width = entry["shape"]
        if entry["dtype"] != "BF16" or width != K or not 0 <= first < rows - 1:
            raise ValueError(f"unexpected weight tensor: {entry}")
        f.seek(8 + length + entry["data_offsets"][0] + first * K * 2)
        raw = f.read(4 * K)
    if len(raw) != 4 * K:
        raise ValueError("short tensor")
    values = [struct.unpack("<f", bytes((0, 0)) + raw[i:i+2])[0] for i in range(0, len(raw), 2)]
    if not all(math.isfinite(v) for v in values):
        raise ValueError("nonfinite weight")
    return [values[:K], values[K:]], {"tensor": name, "shard": file.name, "sha256": sha(raw)}


def clamp(n, lo, hi):
    return min(hi, max(lo, n))


def rne(n, bits):
    q, r = divmod(n, 1 << bits)
    half = 1 << (bits - 1)
    return q + (r > half or (r == half and q % 2 == 1))


def mid(gate, up):
    def lut(i):
        t = (32 * i - 8192) / 1024
        return round(1024 * t / (1 + math.exp(-t)))

    result = []
    for g, u in zip(gate, up, strict=True):
        if g < -8192:
            s = 0
        elif g > 8192:
            s = g
        else:
            i, f = divmod(g + 8192, 32)
            s = lut(i) + rne((lut(min(i + 1, 512)) - lut(i)) * f, 5)
        result.append(clamp(rne(s * u, 10), -32768, 32767))
    return result


def pack(values, bits):
    return sum((v & ((1 << bits) - 1)) << (bits * i) for i, v in enumerate(values))


def vectors(activations, weights):
    """One activation row and two weight lanes across four K8 tiles per segment."""
    for base in range(0, K, 32):
        for k in range(base, base + 32, 8):
            yield pack(activations[k:k+8], 8)
            yield from (0, 0, 0)
        for k in range(base, base + 32, 8):
            yield pack(weights[0][k:k+8] + weights[1][k:k+8], 8)
            yield from (0, 0, 0)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("checkpoint", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--layer", type=int, default=0)
    parser.add_argument("--first-channel", type=int, default=0)
    parser.add_argument("--seed", type=int, default=192)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    rng = random.Random(args.seed)
    # Fixed synthetic post-normalization boundary. Real checkpoint weights.
    activations = [clamp(round(32 * rng.gauss(0, 1)), -128, 127) for _ in range(K)]
    receipt = {
        "checkpoint": args.checkpoint.name, "layer": args.layer,
        "channels": [args.first_channel, args.first_channel + 1],
        "activation": "seeded synthetic S8, scale 2^-5", "activation_seed": args.seed,
        "weight": "BF16 checkpoint rows quantized S8, scale 2^-7",
        "projection": "S64 accumulation; final RNE shift 2 and signed S16 saturation",
        "model_config_sha256": sha((args.checkpoint / "config.json").read_bytes()),
        "weight_index_sha256": sha((args.checkpoint / "model.safetensors.index.json").read_bytes()),
    }
    projections = {}
    for op in ("gate", "up"):
        rows, evidence = extract(args.checkpoint, args.layer, f"{op}_proj", args.first_channel)
        weights = [[clamp(round(x * 128), -128, 127) for x in row] for row in rows]
        evidence["saturated_weights"] = sum(not -128 <= round(x * 128) <= 127 for row in rows for x in row)
        projections[op] = [clamp(rne(sum(a*b for a,b in zip(activations, row, strict=True)), 2),
                                 -32768, 32767) for row in weights]
        (args.output / f"{op}.hex").write_text(
            "".join(f"{word:032x}\n" for word in vectors(activations, weights)), encoding="ascii")
        receipt[op] = evidence
    projections["mid"] = mid(projections["gate"], projections["up"])
    (args.output / "expected.hex").write_text(
        "".join(f"{pack(projections[op], 16):032x}\n" for op in ("gate", "up", "mid")),
        encoding="ascii")
    receipt["results_s16"] = projections
    receipt["output_sha256"] = {f.name: sha(f.read_bytes()) for f in args.output.glob("*.hex")}
    (args.output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()

