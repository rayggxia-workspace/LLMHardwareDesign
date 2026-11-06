"""Convert measured payload routing coverage to a soft compiler cost."""
import argparse
import hashlib
import json
from pathlib import Path
import re


def path_length_dbu(nets):
    """Sum planar lengths of emitted M11/M12 path records."""
    layer = re.compile(r"(?:\+\s+ROUTED|\bNEW)\s+(\w+)")
    point = re.compile(r"\(\s*(-?\d+|\*)\s+(-?\d+|\*)(?:\s+\d+)?\s*\)")
    length = 0
    for body in nets:
        sections = list(layer.finditer(body))
        for index, section in enumerate(sections):
            if section[1] not in {"metal11", "metal12"}:
                continue
            end = sections[index + 1].start() if index + 1 < len(sections) else len(body)
            previous = None
            for x, y in point.findall(body[section.end():end]):
                if (x == "*" or y == "*") and previous is None:
                    raise ValueError("unresolved start coordinate")
                current = (previous[0] if x == "*" else int(x),
                           previous[1] if y == "*" else int(y))
                if previous is not None:
                    length += abs(current[0] - previous[0]) + abs(current[1] - previous[1])
                previous = current
    return length


def feedback(coupon, routed, cost_per_missing, um_per_cost=0):
    if coupon["scope"] != "128-bit payload only" or coupon["expected_nets"] != 128:
        raise ValueError("unsupported coupon scope")
    text = routed.decode()
    net_section, = re.findall(r"^NETS\s+\d+\s*;(.*?)^END NETS\s*$", text, re.M | re.S)
    nets = dict(re.findall(r"^\s*-\s+(up_data_\d+)\s+(.*?);", net_section, re.M | re.S))
    if nets.keys() != {f"up_data_{i}" for i in range(128)}:
        raise ValueError("output DEF does not have the expected FFN payload bundle")
    metal = re.compile(r"(?:\+\s+ROUTED|\bNEW)\s+metal1[12]\b")
    route_missing = sorted(name for name, body in nets.items() if not metal.search(body))
    length = path_length_dbu(nets.values())
    if um_per_cost:
        dbu, = re.findall(r"^UNITS DISTANCE MICRONS (\d+)\s*;", text, re.M)
        length_cost = length // (int(dbu) * um_per_cost)
    else:
        length_cost = 0
    return {
        "base_id": coupon["base_id"],
        "bundle_id": coupon["bundle_id"],
        "kind": "detailed_route_payload_coverage",
        "result": "penalty",
        "evidence_sha256": hashlib.sha256(routed).hexdigest(),
        "coverage_scope": "DEF upper-layer coverage only",
        "incremental_cost": cost_per_missing * len(route_missing) + length_cost,
        "detailed_upper_wire_length_dbu": length,
        "wire_length_cost": length_cost,
        "missing_upper_route": route_missing,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("coupon", type=Path)
    parser.add_argument("routed_def", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--cost-per-missing", type=int, required=True)
    parser.add_argument("--um-per-cost", type=int, default=0)
    args = parser.parse_args()
    if args.cost_per_missing < 0 or args.um_per_cost < 0:
        parser.error("cost must be nonnegative")
    data = feedback(json.loads(args.coupon.read_bytes()), args.routed_def.read_bytes(),
                    args.cost_per_missing, args.um_per_cost)
    args.output.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
