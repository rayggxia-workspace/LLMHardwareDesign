"""Construct a geometry-only trial from an audited joint landing export."""
import argparse
from collections import defaultdict
import csv
import hashlib
import json
from pathlib import Path


def digest(path):
    result = hashlib.sha256()
    with path.open("rb") as source:
        for data in iter(lambda: source.read(1024 * 1024), b""):
            result.update(data)
    return result.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("parent", type=Path)
    parser.add_argument("native", type=Path)
    parser.add_argument("identity", type=Path)
    parser.add_argument("odb", type=Path)
    parser.add_argument("rules", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--scope", required=True)
    parser.add_argument("--prefix", action="append", required=True)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--access-pitch", type=int)
    args = parser.parse_args()
    by_leg = defaultdict(list)
    pins = {}
    with args.parent.open() as source:
        for cut, leg, role, net, *box in csv.reader(source, delimiter="\t"):
            by_leg[cut, int(leg), role, net].append(list(map(int, box)))
    with args.native.open() as source:
        for row in csv.DictReader(source, delimiter="\t"):
            key = row["cut"], int(row["leg"]), row["role"], row["odb_net"]
            by_leg[key].append([int(row[key]) for key in ("x0", "y0", "x1", "y1")])
    groups = defaultdict(lambda: {"driver": [], "sink": []})
    with args.identity.open() as source:
        for row in csv.DictReader(source, delimiter="\t"):
            cut, leg, role, net = row["cut"], int(row["leg"]), row["role"], row["native_net"]
            key = cut, leg, role, net
            if key not in by_leg:
                raise ValueError(f"No exact access geometry for {key}")
            pin = f"{cut}/{leg}"
            if pin in pins:
                raise ValueError(f"Duplicate endpoint {pin}")
            pins[pin] = by_leg.pop(key)
            groups[cut][role].append(pin)
    if by_leg:
        raise ValueError(f"Geometry contains {len(by_leg)} unowned legs")
    selected = []
    for cut, endpoints in sorted(groups.items()):
        if not any(cut.startswith(prefix) for prefix in args.prefix):
            continue
        if len(endpoints["driver"]) != 1 or not endpoints["sink"]:
            raise ValueError(f"Wrong source or receiver count on {cut}")
        selected.append({"id": cut, "driver": endpoints["driver"][0], "sinks": endpoints["sink"]})
    if args.limit:
        selected = selected[:args.limit]
    if not selected:
        raise ValueError("No nets selected")
    rules = json.loads(args.rules.read_text())
    technology = rules["technology"]
    technology["bounds"] = [0, 0, 12360000, 10580000]
    if args.access_pitch:
        technology["access_pitch"] = args.access_pitch
    context = {"scope": args.scope, "physical_qualified": False,
               "dbu_per_micron": 2000, "placement_odb_sha256": digest(args.odb),
               "source_sha256": {key: digest(getattr(args, key)) for key in ("parent", "native", "identity", "rules")}}
    result = {"schema_version": "upper-router/1", "units": "dbu", "technology": technology,
              "pins": pins, "nets": selected, "obstacles": rules["obstacles"], "context": context}
    args.output.write_text(json.dumps(result, separators=(",", ":")) + "\n")
    print(f"actual landing shapes: {len(pins)}; selected nets: {len(selected)}; access pitch: {technology['access_pitch']}")


if __name__ == "__main__":
    main()
