"""Audit functional parity and summarize modeled time for two short replays."""
import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def snapshot(path):
    result = read_json(path / "result.json")
    plan_file = path / "assets/plan.json"
    if digest(plan_file) != result["plan_sha256"]:
        raise ValueError(f"plan checksum differs: {path}")
    plan = read_json(plan_file)
    diary = read_json(path / "progress.json")
    if (len(result["boundary"]) != 2 or diary["boundary"] != result["boundary"] or
            diary["retirements"] != result["retirements"]):
        raise ValueError(f"two matching residual boundaries required: {path}")
    records = result["retirements"]
    if result["mode"] == "decode":
        if (len(records) != 2 or records[0]["selected"] != records[1]["input"] or
                records[1]["time_ps"]-records[0]["time_ps"] != result["interval_ps"]):
            raise ValueError(f"invalid decode boundary: {path}")
    elif records or result["boundary"][-1]["complete_ps"] != result["interval_ps"]:
        raise ValueError(f"invalid prefill boundary: {path}")
    for i, entry in enumerate(result["boundary"]):
        if digest(path / f"residual-{i}.bin") != entry["sha256"]:
            raise ValueError(f"residual checksum differs: {path}")
    for i, entry in enumerate(result["retirements"]):
        if digest(path / f"logits-{i}.bin") != entry["logits_sha256"]:
            raise ValueError(f"logit checksum differs: {path}")
    ddr = result["ddr"]
    if ddr["reads"]+ddr["writes"] != ddr["callbacks"]:
        raise ValueError(f"DDR callbacks do not reconcile: {path}")
    return result, plan, diary


def inference_images(plan):
    images = []
    for item in plan["images"]:
        path = Path(item["path"])
        if path.parent.name == "assets" and (path.name == "local.bin" or path.name.startswith("pos")):
            continue
        images.append((path.name, item["bytes"], item["sha256"]))
    return sorted(images)


def measure(result, diary):
    rows = Counter()
    weights = Counter()
    decode = result["mode"] == "decode"
    for page in diary["pages"]:
        position, group, _ = page["page"].split("-", 2)
        if not decode or position == "pos513":
            family = group if group in ("head", "ingress") else "layers"
            rows[family] += page["complete_ps"] - page["start_ps"]
    for entry in result.get("services", []):
        position, family = entry["group"].split("-", 1)
        if (not decode or position == "pos513") and family == "layers":
            weights[str(entry["signature"][1])] += entry["service_ps"]
    return {"interval_ps": result["interval_ps"], "tok_s": result["tok_s"], "page_ps": dict(rows),
            "layer_service_ps_by_schema": dict(weights), "ddr": result["ddr"],
            "weight_window": result.get("weight_window", 1),
            "ffn_context_cache": result.get("ffn_context_cache", False),
            "compact_kv64": result.get("compact_kv64", False)}


def compare(before, after, same_plan=False):
    a, ap, ad = snapshot(before)
    b, bp, bd = snapshot(after)
    for k in ("mode", "layers", "history"):
        if a[k] != b[k]:
            raise ValueError(f"workload or state differs: {k}")
    row_ratio = 2 if b.get("compact_kv64") and not a.get("compact_kv64") else 1
    for k in ("writes_committed", "cross_step_reads"):
        if a[k] != row_ratio*b[k]:
            raise ValueError(f"KV beat coverage differs: {k}")
    for k in ("recurrent_writes", "recurrent_cross_step_reads", "expert_routes", "residual_saturations"):
        if a.get(k) is not None and b.get(k) is not None and a[k] != b[k]:
            raise ValueError(f"internal state differs: {k}")
    for k in ("first_decode_input", "hidden", "vocab"):
        if ap[k] != bp[k]:
            raise ValueError(f"compiled input or state differs: {k}")
    if row_ratio == 1 and ap["state"] != bp["state"]:
        raise ValueError("compiled state address differs")
    if row_ratio == 2 and (ap["kv_row"], bp["kv_row"], len(ap["state"])) != (512, 256, len(bp["state"])):
        raise ValueError("compact KV must use half the row bytes")
    if inference_images(ap) != inference_images(bp):
        raise ValueError("checkpoint data, inputs, or constants differ")
    if same_plan:
        images = lambda p: [(i["address"], i["bytes"], i["sha256"]) for i in p["images"]]
        if (images(ap) != images(bp) or a["calls"] != b["calls"] or
                any(a["ddr"][k] != b["ddr"][k] for k in ("reads", "writes", "callbacks"))):
            raise ValueError("weight-only comparison requires identical programs and transaction totals")
    for category, keys in (("boundary", ("input_id", "sha256")),
                           ("retirements", ("input", "selected", "vocab", "logits_sha256"))):
        values = lambda result: [tuple(row[key] for key in keys) for row in result[category]]
        if values(a) != values(b):
            raise ValueError(f"functional output differs: {category}")
    return {"model": b["model"], "mode": b["mode"], "layers": b["layers"],
            "before": measure(a, ad), "after": measure(b, bd),
            "throughput_gain_pct": 100*(a["interval_ps"]/b["interval_ps"]-1),
            "baseline_result_sha256": digest(before/"result.json"),
            "candidate_result_sha256": digest(after/"result.json")}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("before", type=Path)
    parser.add_argument("after", type=Path, nargs="?")
    parser.add_argument("--same-plan", action="store_true")
    args = parser.parse_args()
    if args.after:
        output = compare(args.before, args.after, args.same_plan)
    else:
        result, _, diary = snapshot(args.before)
        output = measure(result, diary)
    print(json.dumps(output, indent=2))
