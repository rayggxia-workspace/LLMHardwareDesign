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


def check_pr272(result):
    profile = result.get("pr272_profile")
    if profile in ("ffn", "combined"):
        engines = [p for p in result["ffn_projection"] if p.get("weight_records_consumed")]
        if not engines or any(not 0 < p["weight_read_issues"] == p["weight_read_returns"] or
                              not 0 < p["weight_peak_outstanding"] <= 32 for p in engines):
            raise ValueError("PR #272 FFN requests or credits do not reconcile")
    if profile in ("attention", "combined"):
        services = result["attention_services"]
        if not any(services.values()):
            raise ValueError("PR #272 attention profile has no timed attention")
        for service in services.values():
            if "ddr_issued" in service and (
                    service["ddr_issued"] != service["ddr_returned"] or
                    service["ddr_returned"] != service["s_write_acks"] or
                    service["ddr_peak_inflight"] > 8 or service["reply_slots_peak"] > 16 or
                    service["s_write_peak"] > 4):
                raise ValueError("adapted PR #272 attention did not drain or exceeded its slots")
            if "kv_window_peak" in service and (
                    service["kv_window_peak"] > 8 or service["kv_reserved_slots_peak"] > 16 or
                    service["kv_sram_write_peak"] > 4):
                raise ValueError("archived PR #272 attention exceeded its slots")


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
    measured = {"interval_ps": result["interval_ps"], "tok_s": result["tok_s"], "page_ps": dict(rows),
            "layer_service_ps_by_schema": dict(weights), "ddr": result["ddr"],
            "weight_window": result.get("weight_window", 1),
            "ffn_context_cache": result.get("ffn_context_cache", False),
            "compact_kv64": result.get("compact_kv64", False)}
    if result.get("pr272_profile") not in (None, "off"):
        measured.update(pr272_profile=result["pr272_profile"], ffn_projection=result["ffn_projection"],
                        attention_services=result["attention_services"])
    return measured


def compare(before, after, same_plan=False, same_program=False):
    a, ap, ad = snapshot(before)
    b, bp, bd = snapshot(after)
    check_pr272(b)
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
    if row_ratio == 2 and (ap.get("kv_row", 512), bp["kv_row"], len(ap["state"])) != (512, 256, len(bp["state"])):
        raise ValueError("compact KV must use half the row bytes")
    if inference_images(ap) != inference_images(bp):
        raise ValueError("checkpoint data, inputs, or constants differ")
    if same_plan or same_program:
        images = lambda p: [(i["address"], i["bytes"], i["sha256"]) for i in p["images"]]
        if images(ap) != images(bp) or a["calls"] != b["calls"]:
            raise ValueError("compiled program images or calls differ")
    if same_plan and any(a["ddr"][k] != b["ddr"][k] for k in ("reads", "writes", "callbacks")):
        raise ValueError("weight-only comparison requires identical transaction totals")
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
    parser.add_argument("--same-program", action="store_true")
    args = parser.parse_args()
    if args.after:
        output = compare(args.before, args.after, args.same_plan, args.same_program)
    else:
        result, _, diary = snapshot(args.before)
        output = measure(result, diary)
    print(json.dumps(output, indent=2))
