"""Tiny exhaustive connector-subset oracle, independent of router and validator."""
import itertools
from collections import Counter


def feasible(base, nets, keys):
    if any(type(n.get("width")) is not int or n["width"] <= 0 for n in nets):
        return False
    adjacency = {c: set() for c in base["components"]}
    counts = Counter()
    if len(keys) > base["limits"]["custom_connector_budget"]:
        return False
    for key in keys:
        con = base["connectors"][key]
        ta, tb = con["a"], con["b"]
        counts[ta] += 1
        counts[tb] += 1
        a, b = base["taps"][ta]["component"], base["taps"][tb]["component"]
        adjacency[a].add(b)
        adjacency[b].add(a)
    if any(v > base["taps"][t]["capacity"] for t, v in counts.items()):
        return False
    regions, seen = {}, set()
    for start in adjacency:
        if start in seen:
            continue
        region, stack = set(), [start]
        while stack:
            c = stack.pop()
            if c in region:
                continue
            region.add(c)
            stack.extend(adjacency[c] - region)
        seen.update(region)
        ds = {base["components"][c]["driver"] for c in region
              if base["components"][c]["driver"] is not None}
        if len(ds) > 1:
            return False
        for c in region:
            regions[c] = region
    owners = {}
    for net in nets:
        d = net["driver"]
        if d not in regions or base["components"][d]["driver"] != d:
            return False
        for sink in net["sinks"]:
            if sink not in regions[d] or base["components"][sink]["kind"] != "input":
                return False
            if sink in owners and owners[sink] != d:
                return False
            owners[sink] = d
        if any(base["components"][c]["width"] < net["width"] for c in regions[d]):
            return False
    return True


def solve(base, nets):
    keys = sorted(base["connectors"])
    if len(keys) > 16:
        raise ValueError("Exhaustive oracle limited to at most 16 connectors")
    best = None
    for size in range(len(keys)+1):
        for subset in itertools.combinations(keys, size):
            cost = sum(base["connectors"][k]["cost_units"] for k in subset)
            if best is not None and cost >= best[0]:
                continue
            if feasible(base, nets, subset):
                best = (cost, list(subset))
    return best
