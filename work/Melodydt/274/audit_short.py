"""Check finalized two-position replay coverage and compare compatible FP32 logits."""
import argparse
import json
from pathlib import Path

import numpy as np

from hashlib import sha256


def hash_file(path):
    return sha256(path.read_bytes()).hexdigest()


def audit(run, layers, vocab, mode, reference=None):
    res = json.loads((run / "result.json").read_text())
    plan = json.loads((run / "assets/plan.json").read_text())
    history = 512 if mode == "decode" else 0
    if (res["layers"], res["mode"], res["history"]) != (layers, mode, history):
        raise ValueError("unexpected workload")
    if hash_file(run / "assets/plan.json") != res["plan_sha256"]:
        raise ValueError("unexpected compiled plan")
    if len(plan["phases"]) != 2 or [p["position"] for p in plan["phases"]] != [history, history+1]:
        raise ValueError("missing positions")
    calls = pages = 0
    for phase in plan["phases"]:
        if len(phase["layers"]) != layers or bool(phase["vocabulary"]) != (mode == "decode"):
            raise ValueError("missing layer or vocabulary pages")
        for group in [phase["ingress"], *phase["layers"], phase["vocabulary"]]:
            pages += len(group)
            calls += sum(p["count"] for p in group)
    if pages != res["pages"] or calls != sum(row["count"] for row in res["calls"]):
        raise ValueError("program pages and call counts disagree")
    if res["ddr"]["reads"] + res["ddr"]["writes"] != res["ddr"]["callbacks"]:
        raise ValueError("DDR callbacks mismatch")
    expected = sum(n for _, n in plan["state"])//64
    if (expected, expected//2) != (res["writes_committed"], res["cross_step_reads"]):
        raise ValueError("incorrect cross-position state traffic")
    expected_recurrent = sum(n for _, _, n in plan.get("recurrent_regions", []))//64
    if (expected_recurrent, expected_recurrent//2) != (res.get("recurrent_writes", 0),
                                                        res.get("recurrent_cross_step_reads", 0)):
        raise ValueError("incorrect recurrent state traffic")
    if plan.get("moe"):
        routes = res["expert_routes"]
        if [(r["position"], r["layer"]) for r in routes] != [
                (p["position"], layer) for p in plan["phases"] for layer in range(layers)]:
            raise ValueError("missing MoE layer routes")
        for route in routes:
            if len(set(route["ids"])) != 8 or not all(0 <= k < 40 for k in route["ids"]):
                raise ValueError("incorrect Granite expert selection")
    for i, image in enumerate(res["boundary"]):
        if image["step"] != i or hash_file(run / f"residual-{i}.bin") != image["sha256"]:
            raise ValueError("residual boundary differs")
    numeric = []
    if mode == "decode":
        if len(res["retirements"]) != 2:
            raise ValueError("expected two vocabulary retirements")
        a, b = res["retirements"]
        if a["selected"] != b["input"] or b["time_ps"]-a["time_ps"] != res["interval_ps"]:
            raise ValueError("invalid decode retirement or feedback")
        if reference is not None:
            receipt = json.loads((reference / "reference.json").read_text())
            if receipt["history_payload"] != "zeros":
                raise ValueError("FP32 reference has different initial KV semantics")
        for i, retired in enumerate((a, b)):
            path = run / f"logits-{i}.bin"
            logits = np.fromfile(path, dtype="<i4")
            if (logits.size != vocab or np.argmax(logits) != retired["selected"] or
                    hash_file(path) != retired["logits_sha256"]):
                raise ValueError("vocabulary retirement does not match the committed logits")
            if reference is not None:
                import torch
                target = receipt["decode"][i]
                if retired["input"] != target["input"]:
                    numeric.append({"step": i, "status": "different input token"})
                    continue
                golden = torch.load(reference / f"decode-{i}-logits.pt", weights_only=True).numpy().reshape(-1)
                relative = np.linalg.norm(logits/65536-golden)/np.linalg.norm(golden)
                numeric.append({"step": i, "top1_equal": retired["selected"] == target["selected"],
                                "relative_l2": float(relative)})
    elif res["interval_ps"] != res["boundary"][-1]["complete_ps"]:
        raise ValueError("wrong final-residual timing boundary")
    return {"mode": mode, "layers": layers, "pages": pages, "calls": calls,
            "interval_ps": res["interval_ps"], "tok_s": res["tok_s"], "retirements": res["retirements"],
            "numeric": numeric, "candidate_tlm": True, "result_sha256": hash_file(run / "result.json")}


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("run", type=Path)
    p.add_argument("--layers", type=int, required=True)
    p.add_argument("--vocab", type=int, required=True)
    p.add_argument("--mode", choices=("decode", "prefill"), required=True)
    p.add_argument("--reference", type=Path)
    print(json.dumps(audit(**vars(p.parse_args())), indent=2))
