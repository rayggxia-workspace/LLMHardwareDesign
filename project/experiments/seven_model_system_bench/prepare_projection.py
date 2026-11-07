
"""Prepare one real first-token vocabulary projection slice per frozen checkpoint."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct

from run_systemc import sha256, write_json


def digest(data):
    return hashlib.sha256(data).hexdigest()


def activation(path):
    blob = path.read_bytes()
    exponent, count = struct.unpack_from("<iI", blob)
    offset = 8
    if exponent == -(2 ** 31):
        exponents = struct.unpack_from("<{}i".format(count), blob, offset)
        offset += 4 * count
    else:
        exponents = [exponent] * count
    values = struct.unpack_from("<{}h".format(count), blob, offset)
    if len(blob) != offset + 2 * count:
        raise ValueError("unexpected activation size")
    return [math.ldexp(value, exp) for value, exp in zip(values, exponents)]


def weights(checkpoint, width):
    index = {}
    for line in (checkpoint / "weights.index").read_text().splitlines():
        name, *fields = line.split()
        index[name] = tuple(map(int, fields))
    name = "lm_head.weight" if "lm_head.weight" in index else "model.embed_tokens.weight"
    rows, columns, exponent, offset = index[name]
    if columns != width or rows < 8:
        raise ValueError("unexpected projection dimensions")
    groups = checkpoint / "weights.scales"
    if groups.exists():
        for line in groups.read_text().splitlines():
            parts = line.split()
            if parts and parts[0] == name:
                exponent = int(parts[2])  # The first eight rows share group zero.
                break
    with (checkpoint / "weights.bin").open("rb") as source:
        source.seek(offset)
        blob = source.read(8 * columns * 2)
    values = struct.unpack("<{}h".format(8 * columns), blob)
    return name, digest(blob), [
        [math.ldexp(value, exponent) for value in values[i * columns:(i + 1) * columns]]
        for i in range(8)
    ]


def quantize(values, bits):
    # A shared power-of-two scale per operand vector and round-to-nearest-even.
    maximum = max(map(abs, values))
    hi = (1 << (bits - 1)) - 1
    exponent = math.ceil(math.log2(maximum / hi)) if maximum else 0
    integers = [round(math.ldexp(value, -exponent)) for value in values]
    if any(value < -hi - 1 or value > hi for value in integers):
        raise ValueError("unexpected quantization overflow")
    return integers, exponent


def vectors(name, frozen, checkpoint_root, historical, out):
    run = out / name
    run.mkdir()
    checkpoint = checkpoint_root / Path(frozen["checkpoint"]).name
    for source in ("weights.index", "weights.scales"):
        if source in frozen["checkpoint_inputs"]:
            if sha256(checkpoint / source) != frozen["checkpoint_inputs"][source]["sha256"]:
                raise ValueError("frozen index/scale mismatch: " + source)
    stage = historical / ("run-" + name) / "stage-final-post-norm.bin"
    stage_sha = sha256(stage)
    if stage_sha != frozen["outputs"][stage.name]["sha256"]:
        raise ValueError("frozen activation mismatch")
    a = activation(stage)
    tensor, slice_sha, b = weights(checkpoint, len(a))
    reference = [math.fsum(x * y for x, y in zip(a, row)) for row in b]
    norm = math.sqrt(math.fsum(v * v for v in reference))
    if not norm:
        raise ValueError("zero reference norm")
    formats = {}
    for abits, bbits in ((16, 16), (16, 8), (8, 16), (8, 8)):
        av, aexp = quantize(a, abits)
        packed = [quantize(row, bbits) for row in b]
        bv, bexp = zip(*packed)
        dots = [sum(x * y for x, y in zip(av, row)) for row in bv]
        decoded = [math.ldexp(value, aexp + scale) for value, scale in zip(dots, bexp)]
        rel_l2 = math.sqrt(math.fsum((x - y) ** 2 for x, y in zip(decoded, reference))) / norm
        label = "{}x{}".format(abits, bbits)
        path = run / (label + ".txt")
        lines = [[len(a), abits, bbits], av, *bv, dots]
        path.write_text("".join(" ".join(map(str, line)) + "\n" for line in lines))
        formats[label] = {
            "activation_exponent": aexp, "weight_exponents": list(bexp),
            "max_absolute_error": max(abs(x - y) for x, y in zip(decoded, reference)),
            "relative_l2": rel_l2, "integer_oracle": dots, "fixture_sha256": sha256(path),
        }
    write_json(run / "vectors.json", {
        "checkpoint": checkpoint.name, "tensor": tensor, "row_start": 0, "row_count": 8,
        "input_elements": len(a), "activation_sha256": stage_sha,
        "weight_slice_sha256": slice_sha, "formats": formats, "reference_dots": reference,
        "reference_scope": "dequantized existing checkpoint operands before model-specific logits scaling",
    })


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("frozen", type=Path)
    parser.add_argument("checkpoints", type=Path)
    parser.add_argument("historical", type=Path)
    parser.add_argument("out", type=Path)
    args = parser.parse_args()
    args.out.mkdir()
    reference = json.loads(args.frozen.read_text())["models"]
    for name, frozen in reference.items():
        vectors(name, frozen, args.checkpoints, args.historical, args.out)


if __name__ == "__main__":
    main()
