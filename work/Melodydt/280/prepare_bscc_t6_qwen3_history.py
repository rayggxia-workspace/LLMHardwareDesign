"""Reuse the archived DDR image generated from the frozen Qwen3 FP32 cache."""
from pathlib import Path
import sys


def prepare(source):
    text = source.read_text(encoding="utf-8")
    start = text.index("def materialize(")
    end = text.index("def map_images(", start)
    materialize = '''def materialize(reference, compiler, plan, model, assets):
    archive = Path(environ["QWEN3_FROZEN_HISTORY"])
    frozen_plan = json.loads((archive / "plan.json").read_bytes())
    frozen_result = json.loads((archive.parent / "result.json").read_bytes())
    if file_sha256(archive / "plan.json") != frozen_result["plan_sha256"]:
        raise ValueError("frozen Qwen3 plan digest differs")
    layout_keys = ("history", "layers", "first_decode_input", "state", "kv_row")
    current_layout = json.loads(json.dumps({key: plan[key] for key in layout_keys}))
    if model != "qwen3" or current_layout != {key: frozen_plan[key] for key in layout_keys}:
        raise ValueError("frozen Qwen3 KV layout differs")
    manifest = frozen_plan["representative_history"]
    if (file_sha256(reference / "reference.json") != manifest["reference_sha256"]
            or file_sha256(reference / "history512.pt") != manifest["source_sha256"]):
        raise ValueError("frozen FP32 provenance differs")
    copytree(archive / "representative-history", assets / "representative-history")
    return manifest


'''
    imports = '''from hashlib import sha256
from os import environ
from shutil import copytree
from qwen3_dma_windows import file_sha256'''
    text = (text[:start] + materialize + text[end:]).replace("from hashlib import file_digest, sha256", imports)
    source.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    prepare(Path(sys.argv[1]))
