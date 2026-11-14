"""Distinguish isolated search misses from occupancy-dependent failures."""

import argparse
from collections import defaultdict
from pathlib import Path

from geometry import NativePins
import search
from study import area, read, write
import weighted


def main(args):
    spec = read(args.spec)
    direct = read(args.direct)
    native = NativePins(spec)
    weighted.enable(4)
    groups = defaultdict(list)
    for name, reason in sorted(direct["failed"].items()):
        groups[reason].append(name)
    wanted = {name for group in groups.values() for name in group[:args.per_reason]}
    open_area = area(spec, {})
    occupied = area(spec, direct["routes"])
    evidence = []
    for net in spec["nets"]:
        if net["id"] not in wanted:
            continue
        outcomes = {}
        for label, world in (("isolated", open_area), ("occupied", occupied)):
            route, reason, expanded, _ = search.route_net(net, spec, world.fork(), {}, args.budget, native)
            outcomes[label] = {"found": route is not None, "reason": reason, "expanded": expanded}
        evidence.append({"net": net["id"], "baseline_reason": direct["failed"][net["id"]], **outcomes})
    write(args.output, {"budget": args.budget, "sample_per_reason": args.per_reason, "cases": evidence})


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("spec", type=Path)
    parser.add_argument("direct", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--budget", default=12000, type=int)
    parser.add_argument("--per-reason", default=12, type=int)
    main(parser.parse_args())
