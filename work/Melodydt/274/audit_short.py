"""Check finalized two-position replay coverage and compare compatible FP32 logits."""
import argparse
from hashlib import sha256
import json
from pathlib import Path

import numpy as np


def hash_file(path):
    return sha256(path.read_bytes()).hexdigest()


def prefill_difference(path, model, reference):
    import torch
    from safetensors import safe_open

    receipt = json.loads((reference / "reference.json").read_text())
    checkpoint = Path(receipt["checkpoint"])
    config = json.loads((checkpoint / "config.json").read_text())
    config = config.get("text_config", config)
    key = {
        "gemma": "language_model.model.norm.weight",
        "qwen35": "model.language_model.norm.weight",
        "falcon": "model.final_layernorm.weight",
    }.get(model, "model.norm.weight")
    weight = None
    for shard in sorted(checkpoint.glob("*.safetensors")):
        with safe_open(shard, framework="pt", device="cpu") as source:
            if key in source.keys():
                weight = source.get_tensor(key).float().numpy()
                break
    state = np.fromfile(path, dtype="<i4")/65536
    gold = torch.load(reference / "prefill-post-norm.pt", weights_only=True).numpy().reshape(-1)
    if weight is None or weight.shape != state.shape or state.shape != gold.shape:
        raise ValueError("prefill final residual and reference normalization shapes disagree")
    if model in ("gemma", "qwen35"):
        weight = weight + 1
    eps = config.get("rms_norm_eps", 1e-6)
    modeled = state*weight/np.sqrt(np.mean(state**2)+eps)
    return {"scope": "position 1 residual normalized offline against FP32",
            "relative_l2": float(np.linalg.norm(modeled-gold)/np.linalg.norm(gold)),
            "cosine": float(modeled@gold/(np.linalg.norm(modeled)*np.linalg.norm(gold)))}


def audit(run, layers, vocab, mode, reference=None, aligned_reference=None):
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
    if len(res["boundary"]) != 2:
        raise ValueError("expected two residual boundaries")
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
            if receipt.get("history_payload", "live FP32") != res.get("history_payload", "zeros"):
                raise ValueError("FP32 reference has different initial KV semantics")
            if res.get("history_payload") == "live FP32" and (
                    receipt["outputs"]["history512.pt"] != res.get("history_source_sha256") or
                    not res.get("history_beats")):
                raise ValueError("replay did not consume the matching representative history")
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
        if aligned_reference is not None:
            import torch
            aligned = json.loads((aligned_reference / "comparison-input.json").read_text())
            path = aligned_reference / "decode-1-aligned-logits.pt"
            if (aligned["candidate_first_logits_sha256"] != a["logits_sha256"] or
                    aligned["second_token"] != b["input"] or aligned["fp32_logits_sha256"] != hash_file(path)):
                raise ValueError("aligned FP32 reference differs from this replay")
            golden = torch.load(path, weights_only=True).numpy().reshape(-1)
            logits = np.fromfile(run / "logits-1.bin", dtype="<i4")/65536
            numeric.append({"step": 1, "scope": "same candidate feedback token",
                            "reference_selected": aligned["fp32_selected"],
                            "top1_equal": b["selected"] == aligned["fp32_selected"],
                            "relative_l2": float(np.linalg.norm(logits-golden)/np.linalg.norm(golden))})
    elif res["interval_ps"] != res["boundary"][-1]["complete_ps"]:
        raise ValueError("wrong final-residual timing boundary")
    elif reference is not None:
        model = res.get("model", "qwen3")
        numeric.append(prefill_difference(run / "residual-1.bin", model, reference))
    return {"mode": mode, "layers": layers, "pages": pages, "calls": calls,
            "interval_ps": res["interval_ps"], "tok_s": res["tok_s"], "retirements": res["retirements"],
            "numeric": numeric, "residual_saturations": res.get("residual_saturations"),
            "kv_reads": res["cross_step_reads"], "state_reads": res.get("recurrent_cross_step_reads", 0),
            "ddr_callbacks": res["ddr"]["callbacks"],
            "candidate_tlm": True, "result_sha256": hash_file(run / "result.json")}


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("run", type=Path)
    p.add_argument("--layers", type=int, required=True)
    p.add_argument("--vocab", type=int, required=True)
    p.add_argument("--mode", choices=("decode", "prefill"), required=True)
    p.add_argument("--reference", type=Path)
    p.add_argument("--aligned-reference", type=Path)
    print(json.dumps(audit(**vars(p.parse_args())), indent=2))
