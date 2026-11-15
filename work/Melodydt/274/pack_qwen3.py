"""Prepare and verify Qwen3 N8/K128 native projection weight assets."""
import argparse
import json
from pathlib import Path

from pack_checkpoint_ffn import audit_image, pack_native, sha256
from pack_native_projections import audit_head16, pack_head16
from safetensors import safe_open


PROJECTIONS = ("self_attn.q_proj", "self_attn.k_proj", "self_attn.v_proj",
               "self_attn.o_proj", "mlp.gate_proj", "mlp.up_proj", "mlp.down_proj")


def run(reference, output, part):
    receipt = json.loads(reference.read_text())
    source = Path(receipt["checkpoint"])
    conf = json.loads((source / "config.json").read_text())
    if (conf["model_type"], conf["hidden_size"], conf["num_hidden_layers"]) != ("qwen3", 1024, 28):
        raise ValueError("expected the frozen 28-layer Qwen3 configuration")
    files = sorted(source.glob("*.safetensors"))
    for path in files + [source / "config.json"]:
        if sha256(path) != receipt["checkpoint_files"][path.name]["sha256"]:
            raise ValueError("source input differs from the reference run")
    if part == "head":
        if not conf["tie_word_embeddings"]:
            raise ValueError("expected a tied vocabulary projection")
        names = {"model.embed_tokens.weight": "head"}
        pack, audit = pack_head16, audit_head16
    else:
        first = int(part)
        names = {
            f"model.layers.{i}.{op}.weight": f"L{i:02}-{op}"
            for i in range(first, first + 4) for op in PROJECTIONS
        }
        pack, audit = pack_native, audit_image

    output.mkdir()
    results = {}
    for path in files:
        with safe_open(path, framework="pt", device="cpu") as src:
            for name in sorted(set(src.keys()) & names.keys()):
                matrix = src.get_tensor(name).float().numpy()
                if name in results:
                    raise ValueError("duplicate weight tensor")
                target = output / (names[name] + ".bin")
                error = pack(matrix, target)
                records = audit(matrix, target)
                results[name] = {
                    "shape": list(matrix.shape), "file": target.name, "sha256": sha256(target),
                    "bytes": target.stat().st_size, "records": records, "relative_l2": error,
                }
    if set(results) != set(names):
        raise ValueError("missing checkpoint weights: " + repr(sorted(set(names) - set(results))))
    (output / "receipt.json").write_text(json.dumps({
        "scope": "Qwen3 native projection weight images",
        "source_reference_sha256": sha256(reference),
        "format": "HEAD16/1152 bytes" if part == "head" else "W8A16/N8/K128/1088 bytes",
        "tensors": results,
    }, indent=2) + "\n")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("reference", type=Path)
    p.add_argument("output", type=Path)
    p.add_argument("part", choices=["head", "0", "4", "8", "12", "16", "20", "24"])
    run(**vars(p.parse_args()))
