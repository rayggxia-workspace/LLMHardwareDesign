"""Build checkpoint-backed weight images for the ordinary W8 projection ABI."""

import argparse
import json
from pathlib import Path

import numpy as np

from ffn_scope_emit import RECORD_BYTES
from pack_checkpoint_ffn import audit_image, pack_native, sha256

ORDINARY = "W8A16_n8_k128_ordinary_1088_v1"
HEAD16 = "W8A16_n8_k128_head16_1152_v1"
RECORD_SIZES = {ORDINARY: RECORD_BYTES, HEAD16: 1152}


def projection_size(n, k, base, format_name=ORDINARY):
    if (type(n) is not int or type(k) is not int or not 0 < n < 2**32 or n % 8
            or not 0 < k < 2**16 or k % 128):
        raise ValueError("projection requires representable N8 and K128")
    if format_name not in RECORD_SIZES:
        raise ValueError(f"unsupported projection record format {format_name}")
    size = n // 8 * (k // 128) * RECORD_SIZES[format_name]
    if type(base) is not int or base < 0 or base % 64 or base + size >= 2**48:
        raise ValueError("projection image exceeds the aligned 48-bit aperture")
    return size


def pack_head16(matrix, destination):
    n, k = matrix.shape
    sum_sq = error_sq = 0.0
    with destination.open("xb") as output:
        for group in matrix.reshape(n // 8, 8, k):
            # Store eight K16 groups in K, lane, position order.
            tiles = group.reshape(8, k // 128, 8, 16).transpose(1, 2, 0, 3)
            maximum = np.max(np.abs(tiles), axis=-1)
            scales = np.where(maximum == 0, 1., maximum / 127.).astype("<f2")
            if not np.isfinite(scales).all() or not (scales > 0).all():
                raise ValueError("head16 scale outside native positive FP16")
            decoded = scales.astype(np.float32)[..., None]
            weight = np.rint(tiles / decoded).clip(-128, 127).astype(np.int8)
            records = np.empty((k // 128, RECORD_SIZES[HEAD16]), dtype=np.uint8)
            records[:, :1024] = weight.reshape(k // 128, 1024).view(np.uint8)
            records[:, 1024:] = np.ascontiguousarray(scales).view(np.uint8).reshape(k // 128, 128)
            output.write(records.tobytes())
            sum_sq += float(np.square(tiles, dtype=np.float64).sum())
            error_sq += float(np.square(weight * decoded - tiles, dtype=np.float64).sum())
    return (error_sq / sum_sq) ** .5 if sum_sq else 0.


def audit_head16(matrix, path):
    n, k = matrix.shape
    k_tiles = k // 128
    records = np.memmap(path, dtype=np.uint8, mode="r", shape=(n // 8, k_tiles, RECORD_SIZES[HEAD16]))
    lanes = np.arange(8)[:, None]
    positions = np.arange(128)[None, :]
    offsets = (positions // 16) * 128 + lanes * 16 + positions % 16
    for group, row in enumerate(records):
        # Independently read lane-major values from their native byte offsets.
        source = np.stack(np.split(matrix[group * 8:(group + 1) * 8], k_tiles, axis=1))
        source = source.reshape(k_tiles, 8, 8, 16)
        magnitude = np.max(np.abs(source), axis=-1)
        expected_scale = np.where(magnitude == 0, 1., magnitude / 127.).astype("<f2")
        scales = np.ascontiguousarray(row[:, 1024:]).view("<f2").reshape(k_tiles, 8, 8).transpose(0, 2, 1)
        expected = np.rint(source / scales.astype(np.float32)[..., None]).clip(-128, 127)
        if not np.array_equal(scales, expected_scale) or not np.array_equal(
                row[:, offsets].view(np.int8).reshape(k_tiles, 8, 8, 16), expected):
            raise ValueError(f"head16 record mismatch in group {group}")
    return n // 8 * k_tiles


def pack_projections(checkpoint, reference, entries, output):
    from safetensors import safe_open

    shards = sorted(checkpoint.glob("*.safetensors"))
    actual = {path.name: sha256(path) for path in [*shards, checkpoint / "config.json"]}
    if not shards or actual != reference["checkpoint_files_sha256"]:
        raise ValueError("checkpoint does not match frozen reference")
    if not entries:
        raise ValueError("projection list is empty")
    bindings = {}
    regions = []
    source_keys = {}
    for index, entry in enumerate(entries):
        name = entry["tensor"]
        if name in bindings:
            raise ValueError(f"duplicate logical projection {name}")
        n, k = entry["shape"]
        base = entry["base"]
        format_name = entry.get("format", ORDINARY)
        size = projection_size(n, k, base, format_name)
        regions.append((base, base + size, name))
        bindings[name] = dict(entry, format=format_name, bytes=size, file=f"projection-{index:04d}.bin")
        source_keys[name] = entry.get("checkpoint_tensor", name)
    regions.sort()
    for left, right in zip(regions, regions[1:]):
        if left[1] > right[0]:
            raise ValueError(f"projection address overlap: {left[2]} and {right[2]}")

    source_shards = {}
    for shard in shards:
        with safe_open(shard, framework="pt", device="cpu") as handle:
            for key in handle.keys():
                if key in source_shards:
                    raise ValueError(f"duplicate checkpoint tensor {key}")
                source_shards[key] = shard
    for name, binding in bindings.items():
        for key in (source_keys[name], binding.get("bias_tensor")):
            if key is not None and key not in source_shards:
                raise ValueError(f"missing checkpoint tensor {key} for {name}")

    output.mkdir(parents=True, exist_ok=False)
    for name, binding in bindings.items():
        key = source_keys[name]
        shard = source_shards[key]
        with safe_open(shard, framework="pt", device="cpu") as handle:
            matrix = handle.get_tensor(key).float().numpy()
        if list(matrix.shape) != binding["shape"] or not np.isfinite(matrix).all():
            raise ValueError(f"shape or finite-value check failed for {key}")
        destination = output / binding["file"]
        pack, audit = (pack_head16, audit_head16) if binding["format"] == HEAD16 else (pack_native, audit_image)
        error = pack(matrix, destination)
        if destination.stat().st_size != binding["bytes"]:
            raise ValueError(f"unexpected record image length for {key}")
        records = audit(matrix, destination)
        binding.update(checkpoint_tensor=key, shard=shard.name, sha256=sha256(destination),
                       audited_records=records, weight_reconstruction_relative_l2=error)
        bias = binding.get("bias_tensor")
        if bias is not None:
            with safe_open(source_shards[bias], framework="pt", device="cpu") as handle:
                values = handle.get_tensor(bias).float().numpy()
            if values.shape != (binding["shape"][0],) or not np.isfinite(values).all():
                raise ValueError(f"shape or finite-value check failed for {bias}")
            bias_path = destination.with_suffix(".bias.f32le")
            with bias_path.open("xb") as stream:
                stream.write(values.astype("<f4", copy=False).tobytes())
            binding["bias"] = dict(file=bias_path.name, sha256=sha256(bias_path),
                                   format="checkpoint_fp32_le")
    manifest = dict(schema="native-w8-projection-assets/1", checkpoint_sha256=actual,
                    projections=bindings)
    with (output / "projection-images.json").open("x", encoding="utf-8") as stream:
        json.dump(manifest, stream, indent=2)
        stream.write("\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkpoint", type=Path)
    parser.add_argument("reference_receipt", type=Path)
    parser.add_argument("projection_spec", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    reference = json.loads(args.reference_receipt.read_text(encoding="utf-8"))
    entries = json.loads(args.projection_spec.read_text(encoding="utf-8"))
    pack_projections(args.checkpoint, reference, entries, args.output)


if __name__ == "__main__":
    main()
