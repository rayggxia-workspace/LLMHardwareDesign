"""Convert measured payload routing coverage to a soft compiler cost."""
import argparse
import hashlib
import json
from pathlib import Path
import re


def feedback(coupon, routed, cost_per_missing):
    if coupon["scope"] != "128-bit payload only" or coupon["expected_nets"] != 128:
        raise ValueError("unsupported coupon scope")
    text = routed.decode()
    net_section, = re.findall(r"^NETS\s+\d+\s*;(.*?)^END NETS\s*$", text, re.M | re.S)
    nets = dict(re.findall(r"^\s*-\s+(up_data_\d+)\s+(.*?);", net_section, re.M | re.S))
    if nets.keys() != {f"up_data_{i}" for i in range(128)}:
        raise ValueError("output DEF does not have the expected FFN payload bundle")
    metal = re.compile(r"(?:\+\s+ROUTED|\bNEW)\s+metal1[12]\b")
    route_missing = sorted(name for name, body in nets.items() if not metal.search(body))
    return {
        "base_id": coupon["base_id"],
        "bundle_id": coupon["bundle_id"],
        "kind": "detailed_route_payload_coverage",
        "result": "penalty",
        "evidence_sha256": hashlib.sha256(routed).hexdigest(),
        "coverage_scope": "DEF upper-layer coverage only",
        "incremental_cost": cost_per_missing * len(route_missing),
        "missing_upper_route": route_missing,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("coupon", type=Path)
    parser.add_argument("routed_def", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--cost-per-missing", type=int, required=True)
    args = parser.parse_args()
    if args.cost_per_missing < 0:
        parser.error("cost must be nonnegative")
    data = feedback(json.loads(args.coupon.read_bytes()), args.routed_def.read_bytes(),
                    args.cost_per_missing)
    args.output.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
