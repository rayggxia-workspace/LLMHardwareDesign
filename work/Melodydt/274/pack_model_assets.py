"""Pack and audit model projection assets with the #260 record encoders."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from pack_checkpoint_ffn import audit_image, pack_native, sha256
from pack_native_projections import audit_head16, pack_head16
from safetensors import safe_open


def chosen(name):
    return (
        "vision" not in name and ".mtp." not in name and "multi_modal" not in name
        and name.endswith(".weight") and (
            name.endswith(("embed_tokens.weight", "lm_head.weight"))
            or ".layers." in name and (
                name.endswith("_proj.weight") or name.endswith("router.layer.weight")
                or name.endswith(("input_linear.weight", "output_linear.weight")))))


def matrices(key, values):
    if values.ndim == 2:
        yield key, values
    elif values.ndim == 3 and ".block_sparse_moe." in key:
        for index, expert in enumerate(values):
            yield f"{key}.expert{index:02d}", expert
    else:
        raise ValueError(f"unsupported matrix shape for {key}: {values.shape}")


def rounded_zero_tiles(matrix):
    """FP16 scale underflow implies every INT8 coefficient in the group is zero."""
    groups = matrix.reshape(matrix.shape[0], -1, 128)
    peak = np.max(np.abs(groups), axis=-1)
    mask = (peak > 0) & ((peak / 127).astype(np.float16) == 0)
    if np.any(mask):
        matrix = matrix.copy()
        matrix.reshape(groups.shape)[mask] = 0
    return matrix, int(np.count_nonzero(mask))


def model_assets(reference, output):
    raw = reference.read_bytes()
    receipt = json.loads(raw)
    source = Path(receipt["checkpoint"])
    weights = sorted(source.glob("*.safetensors"))
    config = source / "config.json"
    for p in [config, *weights]:
        if sha256(p) != receipt["checkpoint_files"][p.name]["sha256"]:
            raise ValueError(f"input checksum mismatch: {p}")
    model = json.loads(config.read_text())
    text = model.get("text_config", model)
    tied = text.get("tie_word_embeddings", model.get("tie_word_embeddings", True))
    output.mkdir()
    result = {}
    for shard in weights:
        with safe_open(shard, framework="pt", device="cpu") as handle:
            for key in sorted(name for name in handle.keys() if chosen(name)):
                values = handle.get_tensor(key).float().numpy()
                embedding = key.endswith("embed_tokens.weight")
                if embedding:
                    path = output / "embedding.s32"
                    (np.rint(values * 65536).astype("<i4")).tofile(path)
                    result["embedding"] = {
                        "source_tensor": key, "shape": list(values.shape), "file": path.name,
                        "bytes": path.stat().st_size, "sha256": sha256(path), "format": "S32/Q16",
                    }
                    if not tied:
                        continue
                head = embedding or key.endswith("lm_head.weight")
                name = "head" if head else key
                for target, matrix in matrices(name, values):
                    if target in result:
                        raise ValueError(f"duplicate packed tensor: {target}")
                    n, k = matrix.shape
                    pn = (n + 7) & -8
                    pk = (k + 127) & -128
                    if (pn, pk) != matrix.shape:
                        matrix = np.pad(matrix, [(0, pn - n), (0, pk - k)])
                    zeroed = 0
                    removed_sq = 0.0
                    original_sq = None
                    if ".expert" in target:
                        original = matrix
                        matrix, zeroed = rounded_zero_tiles(matrix)
                        if zeroed:
                            removed_sq = float(np.square(original-matrix, dtype=np.float64).sum())
                            original_sq = float(np.square(original, dtype=np.float64).sum())
                    path = output / (target + ".bin")
                    pack, audit = (pack_head16, audit_head16) if head else (pack_native, audit_image)
                    rel = pack(matrix, path)
                    nrecords = audit(matrix, path)
                    if zeroed:
                        rel = (rel**2*(original_sq-removed_sq)/original_sq
                               + removed_sq/original_sq)**0.5
                    result[target] = {
                        "source_tensor": key, "shape": [n, k], "padded_shape": [pn, pk],
                        "file": path.name, "bytes": path.stat().st_size, "sha256": sha256(path),
                        "records": nrecords, "relative_l2": rel,
                        "fp16_scale_underflow_groups": zeroed,
                        "format": "HEAD16/1152" if head else "W8A16/1088",
                    }
    if not {"embedding", "head"} <= result.keys() or len(result) <= 2:
        raise ValueError("model does not include embedding, vocabulary and layer weights")
    (output / "receipt.json").write_text(json.dumps({
        "model": receipt["model"], "reference_sha256": hashlib.sha256(raw).hexdigest(),
        "tensors": result, "scope": "matrix assets; padded lanes are outside logical vocabulary",
    }, indent=2) + "\n")
    print(receipt["model"], len(result), sum(t.get("records", 0) for t in result.values()), flush=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("reference", type=Path)
    p.add_argument("output", type=Path)
    a = p.parse_args()
    model_assets(a.reference, a.output)
