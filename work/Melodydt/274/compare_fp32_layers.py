"""Compare candidate residual snapshots with a matching FP32 workload."""
import argparse
from hashlib import sha256
import json
from pathlib import Path

import numpy as np


def load(path):
    return json.loads(path.read_text())


def compare(reference, fp32, candidate):
    ref = load(reference / "reference.json")
    expected = load(fp32 / "trace.json")
    trace = load(candidate / "layer-trace.json")
    result = load(candidate / "result.json")
    if expected["reference_sha256"] != sha256((reference / "reference.json").read_bytes()).hexdigest():
        raise ValueError("FP32 trace uses a different reference receipt")
    decode = result["mode"] == "decode"
    if decode and trace["initial_state_sha256"] != expected["history_source_sha256"]:
        raise ValueError("decode starts from a different cache")
    ids = load(reference / "input-ids.json")
    targets = {item["file"]: item["sha256"] for item in expected["frames"]}
    rows = []
    for item in trace["frames"]:
        phase, step, _, layer = Path(item["file"]).stem.split("-")
        step, layer = int(step), int(layer)
        token = ref["decode"][step]["input"] if decode else ids[step]
        if item["input"] != token:
            continue
        raw = (candidate / item["file"]).read_bytes()
        gold_name = f"{phase}-{step}-layer-{layer}.f32"
        gold_raw = (fp32 / gold_name).read_bytes()
        if sha256(raw).hexdigest() != item["sha256"] or sha256(gold_raw).hexdigest() != targets[gold_name]:
            raise ValueError("residual snapshot SHA-256 mismatch")
        values = np.frombuffer(raw, dtype="<i4").astype(np.float64)/(1 << trace.get("fraction_bits", 16))
        gold = np.frombuffer(gold_raw, dtype="<f4").astype(np.float64)
        if values.shape != gold.shape or not np.isfinite(gold).all():
            raise ValueError("hidden shape or values differ")
        norm, candidate_norm = np.linalg.norm(gold), np.linalg.norm(values)
        rows.append({"step": step, "layer": layer,
                     "relative_l2": float(np.linalg.norm(values-gold)/norm) if norm else None,
                     "cosine": float(np.dot(values, gold)/(norm*candidate_norm)) if norm*candidate_norm else None,
                     "candidate_max_abs": float(np.max(np.abs(values))),
                     "fp32_max_abs": float(np.max(np.abs(gold))),
                     "saturations": item["saturations"]})
    return {"model": result["model"], "mode": result["mode"], "rows": rows}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("reference", "fp32", "candidate"):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    print(json.dumps(compare(**vars(args)), indent=2))
