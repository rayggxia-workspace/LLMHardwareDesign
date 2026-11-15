"""Pack pinned Qwen2.5-3B FFN layers for the native W8/A16 weight ABI."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from ffn_scope_emit import layout, RECORD_BYTES


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def pack_native(matrix, destination):
    if matrix.ndim != 2 or matrix.shape[0] % 8 or matrix.shape[1] % 128:
        raise ValueError("native records require full N8 and K128 tiles")
    n, k = matrix.shape
    sum_sq = error_sq = 0.0
    with destination.open("xb") as output:
        for group in matrix.reshape(n // 8, 8, k):
            tile = group.reshape(8, k // 128, 128).transpose(1, 0, 2)
            maximum = np.abs(tile).max(axis=2)
            scale = np.where(maximum != 0, maximum / 127, 1).astype("<f2")
            if not np.isfinite(scale).all() or not (scale > 0).all():
                raise ValueError("weight scale outside native positive FP16")
            decoded_scale = scale.astype(np.float32)[..., None]
            quantized = np.clip(np.rint(tile / decoded_scale), -127, 127).astype(np.int8)
            records = np.zeros((k // 128, RECORD_BYTES), dtype=np.uint8)
            records[:, :1024] = (quantized.reshape(-1, 8, 8, 16)
                                 .transpose(0, 2, 1, 3).reshape(-1, 1024).view(np.uint8))
            records[:, 1024:1040] = np.ascontiguousarray(scale).view(np.uint8).reshape(-1, 16)
            output.write(records.tobytes())
            sum_sq += float(np.square(tile, dtype=np.float64).sum())
            error_sq += float(np.square(quantized * decoded_scale - tile, dtype=np.float64).sum())
    if destination.stat().st_size != layout(k, n):
        raise RuntimeError("packed image length mismatch")
    return (error_sq / sum_sq) ** .5 if sum_sq else 0.0


def audit_image(matrix, path):
    n, k = matrix.shape
    k_tiles = k // 128
    # Independently decode the record via the byte address for each lane/K position.
    lanes = np.arange(8)[:, None]
    positions = np.arange(128)[None, :]
    offsets = (positions // 16) * 128 + lanes * 16 + positions % 16
    records = np.memmap(path, dtype=np.uint8, mode="r", shape=(n // 8, k_tiles, RECORD_BYTES))
    for group, row in enumerate(records):
        if row[:, 1040:].any():
            raise ValueError("nonzero reserved weight bytes")
        stored_scales = np.ascontiguousarray(row[:, 1024:1040]).view("<f2").reshape(k_tiles, 8)
        tiles = np.stack(np.split(matrix[group * 8:(group + 1) * 8], k_tiles, axis=1))
        magnitude = np.max(np.abs(tiles), axis=-1)
        expected_scales = np.where(magnitude == 0, 1., magnitude.astype(np.float64) / 127).astype("<f2")
        if not np.array_equal(stored_scales, expected_scales):
            raise ValueError(f"record scale lane/order mismatch in group {group}")
        expected = np.rint(tiles / stored_scales.astype(np.float32)[..., None]).clip(-127, 127)
        if not np.array_equal(row[:, offsets].view(np.int8), expected):
            raise ValueError(f"record weight order mismatch in group {group}")
    return n // 8 * k_tiles


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkpoint", type=Path)
    parser.add_argument("reference_receipt", type=Path)
    parser.add_argument("output", type=Path)
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument("--layer", type=int)
    selection.add_argument("--all-layers", action="store_true")
    args = parser.parse_args()
    if args.layer is not None and not 0 <= args.layer < 36:
        parser.error("layer must be in [0,36)")
    from safetensors import safe_open

    source = json.loads(args.reference_receipt.read_text())["checkpoint_files_sha256"]
    actual = {path.name: sha256(path) for path in
              [*sorted(args.checkpoint.glob("*.safetensors")), args.checkpoint / "config.json"]}
    if actual != source:
        raise ValueError("checkpoint does not match frozen reference")
    layers = range(36) if args.all_layers else [args.layer]
    operations = ("gate", "up", "down")
    names = {f"model.layers.{layer}.mlp.{operation}_proj.weight": (layer, operation)
             for layer in layers for operation in operations}
    args.output.mkdir(parents=True, exist_ok=False)
    destinations = {layer: args.output / f"layer-{layer:02d}" if args.all_layers else args.output
                    for layer in layers}
    for directory in destinations.values():
        directory.mkdir(exist_ok=True)
    results = {layer: {} for layer in layers}
    for shard in sorted(args.checkpoint.glob("*.safetensors")):
        with safe_open(shard, framework="pt", device="cpu") as handle:
            keys = set(handle.keys())
            for tensor, (layer, name) in names.items():
                if tensor not in keys:
                    continue
                if name in results[layer]:
                    raise ValueError("duplicate native weight tensor")
                matrix = handle.get_tensor(tensor).float().numpy()
                expected = (2048, 11008) if name == "down" else (11008, 2048)
                if matrix.shape != expected or not np.isfinite(matrix).all():
                    raise ValueError(f"unexpected shape or non-finite values for {tensor}")
                output = destinations[layer] / f"{name}.bin"
                error = pack_native(matrix, output)
                audited_records = audit_image(matrix, output)
                results[layer][name] = dict(tensor=tensor, shard=shard.name, shape=list(matrix.shape),
                                     file=output.name, bytes=output.stat().st_size, sha256=sha256(output),
                                     format="W8A16_n8_k128_ordinary_1088_v1", audited_records=audited_records,
                                     weight_reconstruction_relative_l2=error)
    for layer, images in results.items():
        if set(images) != set(operations):
            raise ValueError(f"checkpoint is missing required FFN matrices in layer {layer}")
        manifest = dict(checkpoint_sha256=actual, layer=layer, quantization="W8 RNE per lane/K128, scale FP16",
                        scope="weight image and record audit; model numeric quality unverified",
                        packed_weights=images)
        (destinations[layer] / "weight-images.json").write_text(json.dumps(manifest, indent=2) + "\n",
                                                               encoding="ascii")
    if args.all_layers:
        manifests = {layer: str((destinations[layer] / "weight-images.json").relative_to(args.output))
                     for layer in layers}
        index = dict(checkpoint_sha256=actual, layers=manifests, scope="FFN images only")
        (args.output / "index.json").write_text(json.dumps(index, indent=2) + "\n", encoding="ascii")


if __name__ == "__main__":
    main()
