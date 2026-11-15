"""Audit both finalized benchmark phases against an independent FP32 reference."""
import argparse
import hashlib
import json
from pathlib import Path

from audit_short import audit
from compare_fp32_layers import compare


def do_audit(reference, fp32, prefill, decode):
    records = {}
    for mode, path in (("prefill", prefill), ("decode", decode)):
        result_file = path / "result.json"
        result = json.loads(result_file.read_text())
        plan = json.loads((path / "assets/plan.json").read_text())
        if plan.get("three_p") is not True:
            raise ValueError("expected the compiled three-P deployment")
        if result["residual_saturations"]:
            raise ValueError("residual saturation during qualified replay")
        for group in ("ffn_by_target", "expert_down_by_target"):
            if group not in result and group == "expert_down_by_target" and not plan.get("moe"):
                continue
            stats = result[group]
            if set(stats) != {"0", "1", "2"} or any(
                    not s["weight_records_consumed"] or
                    not 0 < s["weight_read_issues"] == s["weight_read_returns"] for s in stats.values()):
                raise ValueError("three-P record and callback audit failed")
        summary = audit(path, result["layers"], plan["vocab"], mode, reference)
        if mode == "decode" and not all(item.get("top1_equal") for item in summary["numeric"]):
            raise ValueError(f"FP32 token divergence: {summary['numeric']}")
        trace = compare(reference, fp32, path)
        if len(trace["rows"]) != 2 * result["layers"]:
            raise ValueError("FP32 layer traces did not cover both positions")
        summary["layer_trace"] = trace["rows"]
        summary["result_sha256"] = hashlib.sha256(result_file.read_bytes()).hexdigest()
        records[mode] = summary
    return records


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("reference", "fp32", "prefill", "decode"):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    print(json.dumps(do_audit(**vars(args)), indent=2))
