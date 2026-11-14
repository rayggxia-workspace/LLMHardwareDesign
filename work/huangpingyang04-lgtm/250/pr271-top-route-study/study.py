"""Run the PR #271 toy comparison with the PR #259 routing and geometry checks."""

import argparse
from collections import Counter, defaultdict
import csv
import json
from pathlib import Path
import re
from time import monotonic

from check import digest, verify
from geometry import NativePins, Occupancy, access_points, net_priority, RoutingGrid, via_shapes
from handoff import verify_handoff
from repeaters import check_allocations, inventory, physical_nets, projection
from resource_search import estimated_load, length
import search
import weighted


DBU = 2000
CAP = .155390385 * 1.5
VIA_CAP = .2
SOURCE = "BUF_X4"
REPEATER = "BUF_X32"
RECEIVER = "DFF_X1"


def read(path):
    return json.loads(path.read_bytes())


def write(path, data):
    with path.open("x", encoding="utf-8") as out:
        json.dump(data, out, separators=(",", ":"))
        out.write("\n")


def cell_property(lib, cell, pin, key):
    block = re.search(r"\bcell\s*\(\s*" + cell + r"\s*\)\s*\{(.*?)(?=\bcell\s*\(|\Z)", lib, re.S)[1]
    terminal = re.search(r"\bpin\s*\(\s*" + pin + r"\s*\)\s*\{(.*?)(?=\bpin\s*\(|\Z)", block, re.S)[1]
    return float(re.search(r"\b" + key + r"\s*:\s*([\d.eE+-]+)", terminal)[1])


def load_model(lib, spec):
    return {
        "wire_cap_ff_per_dbu": CAP / DBU, "via10_cap_ff": VIA_CAP, "via11_cap_ff": VIA_CAP,
        "driver_limits_ff": {net["driver"]: cell_property(lib, SOURCE, "Z", "max_capacitance")
                             for net in spec["nets"][:1]},
        "sink_cap_ff": cell_property(lib, RECEIVER, "D", "capacitance"),
        "relay_cap_ff": cell_property(lib, REPEATER, "A", "capacitance"),
        "relay_limit_ff": cell_property(lib, REPEATER, "Z", "max_capacitance"),
    }


def electrical_inputs(model, spec):
    limit = next(iter(model["driver_limits_ff"].values()))
    return {
        **{key: model[key] for key in ("wire_cap_ff_per_dbu", "via10_cap_ff", "via11_cap_ff")},
        "driver_limits_ff": {n["driver"]: limit for n in spec["nets"]},
        "sink_caps_ff": {p: model["sink_cap_ff"] for n in spec["nets"] for p in n["sinks"]},
    }


def family_stats(families, failures, routes, loads):
    result = {}
    for family in sorted(set(families.values())):
        ids = [net for net, group in families.items() if group == family]
        result[family] = {
            "nets": len(ids),
            "routed": sum(net in routes for net in ids),
            "failed": dict(Counter(failures[net] for net in ids if net in failures)),
            "overload_nets": sum(any(leg["over_ff"] > 0 for leg in loads.get(net, ())) for net in ids),
        }
    return result


def geometry_result(spec, routes, failures):
    return {
        "schema_version": "upper-router-result/1", "routes": routes, "failed": failures,
        "status": "partial" if failures else "geometry_complete", "physical_qualified": False,
        "electrical_status": "not_evaluated", "timing_status": "not_evaluated",
        "context": spec["context"], "spec_sha256": digest(spec),
    }


def compact(route, net, spec):
    """Merge contiguous same-direction segments when the original grid admits the span."""
    grid = RoutingGrid(spec["technology"], (spec["pins"][pin] for pin in [net["driver"], *net["sinks"]]))
    segments = []
    for edge in route["segments"]:
        if segments:
            prev = segments[-1]
            axis = int(edge["layer"] == "M12")
            if (edge["layer"] == prev["layer"] and prev["b"] == edge["a"]
                    and (prev["b"][axis] - prev["a"][axis]) * (edge["b"][axis] - edge["a"][axis]) > 0
                    and grid.allows(prev["a"], edge["b"])):
                prev["b"] = edge["b"]
                continue
        segments.append(dict(edge))
    return {**route, "segments": segments}


def area(spec, routes, omit=None, reserve_access=False):
    book = Occupancy(spec["technology"])
    book.add([(row["layer"], row["rect"]) for row in spec.get("obstacles", [])], None)
    if reserve_access:
        tech = spec["technology"]
        for net in spec["nets"]:
            for pin in (net["driver"], *net["sinks"]):
                candidates = access_points(spec["pins"][pin], tech)
                if len(candidates) == 1:
                    book.add(via_shapes("via10", candidates[0], tech), net["id"])
    for owner, route in routes.items():
        if owner != omit:
            book.add(search.route_shapes(route, spec["technology"]), owner)
    return book


def baseline(spec, rounds, budget, reserve_access):
    net_priority_rank = net_priority(spec)
    order = sorted(spec["nets"], key=lambda net: net_priority_rank[net["id"]])
    best = {}, {n["id"]: "search_not_found" for n in order}
    native = NativePins(spec)
    history = defaultdict(int)
    for epoch in range(rounds):
        started = monotonic()
        scene = area(spec, {}, reserve_access=reserve_access)
        routes, failures = {}, {}
        for index, net in enumerate(order, 1):
            name = net["id"]
            trial = scene.fork()
            wire, reason, _, blocks = search.route_net(net, spec, trial, history, budget, native)
            for point in blocks:
                history[point] += 1
            if wire is None:
                failures[name] = reason
            else:
                wire = compact(wire, net, spec)
                scene.add(search.route_shapes(wire, spec["technology"]), name)
                routes[name] = wire
            if index % 100 == 0:
                print("direct", epoch + 1, index, len(routes), len(failures), round(monotonic() - started), flush=True)
        if len(routes) > len(best[0]):
            best = routes, failures
        if not failures:
            break
        order.sort(key=lambda n: (n["id"] not in failures, net_priority_rank[n["id"]]))
    return geometry_result(spec, *best)


def inside(point, rect, margin):
    return rect[0] - margin <= point[0] <= rect[2] + margin and rect[1] - margin <= point[1] <= rect[3] + margin


def distance(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def footprint_sites(net, spec, blocks, terminals):
    tech = spec["technology"]
    pitch = tech["pitch"]
    origin = tech["origin"]
    bounds = tech["bounds"]
    ends = [access_points(spec["pins"][pin], tech)[0] for pin in [net["driver"], *net["sinks"]]]
    source = ends[0]
    target = max(ends[1:], key=lambda end: distance(source, end))
    anchors = []
    for fraction in (.15, .25, .35, .45, .55, .70, .85):
        x = int(source[0] + fraction * (target[0] - source[0]))
        y = int(source[1] + fraction * (target[1] - source[1]))
        anchors += [(x, y), (x, source[1]), (source[0], y), (x, target[1]), (target[0], y)]
    for rect in blocks:
        x0, y0, x1, y1 = rect
        for x, y in list(anchors[:35]):
            cx, cy = max(x0, min(x, x1)), max(y0, min(y, y1))
            anchors += [(x0-3*pitch, cy), (x1+3*pitch, cy), (cx, y0-3*pitch), (cx, y1+3*pitch)]
    candidates = {}
    for x, y in anchors:
        bx, by = (round((z-o)/pitch)*pitch+o for z, o in zip((x, y), origin))
        for ox, oy in ((0, 0), (-3, 0), (3, 0), (0, -3), (0, 3), (-5, 3), (5, -3)):
            a = bx + ox*pitch, by + oy*pitch
            z = a[0] + 2*pitch, a[1]
            if a in candidates or not all(inside(point, bounds, -3*pitch) for point in (a, z)):
                continue
            if any(inside(point, block, 2*pitch) for block in blocks for point in (a, z)):
                continue
            if any((a[0]+i*pitch, a[1]) in terminals for i in range(-2, 5)):
                continue
            candidates[a] = z
    return ends, candidates


def rank_sites(net, spec, blocks, unavailable, model, cap_limit, sink_count, failed, reserve):
    ends, sites = footprint_sites(net, spec, blocks, unavailable)
    source, *sinks = ends
    rows = []
    for a, z in sites.items():
        if any(abs(a[1]-other[1]) < 2*spec["technology"]["pitch"]
               and abs(a[0]-other[0]) < 4*spec["technology"]["pitch"] for other in reserve):
            continue
        before = distance(source, a)
        after = max(distance(z, sink) for sink in sinks)
        ratios = ((before/DBU*CAP+model["relay_cap_ff"])/cap_limit,
                  (after/DBU*CAP+sink_count*model["sink_cap_ff"])/model["relay_limit_ff"])
        deviation = before + after - max(distance(source, p) for p in sinks)
        score = (sum(max(0, ratio-1) for ratio in ratios), deviation, max(ratios), before + after)
        if failed:
            score = (max(before, after), *score)
        rows.append((score, a, z, ratios))
    return sorted(rows)


def make_relay(a, z, model):
    name = f"gap-{a[0]}-{a[1]}"
    def pad(p):
        return [[p[0]-2000, p[1]-2000, p[0]+2000, p[1]+2000]]
    return {
        "id": name, "status": "virtual", "power": "assumed",
        "footprint_dbu": [a[0]-2400, a[1]-2400, z[0]+2400, z[1]+2400],
        "input": {"id": name+"/A", "m10": pad(a)}, "output": {"id": name+"/Z", "m10": pad(z)},
        "input_cap_ff": model["relay_cap_ff"], "output_limit_ff": model["relay_limit_ff"],
    }


def repair(spec, direct, blocks, model, budget, max_targets, candidate_count):
    phase = monotonic()
    nets = {net["id"]: net for net in spec["nets"]}
    electrical = electrical_inputs(model, spec)
    caps, limits = electrical["sink_caps_ff"], electrical["driver_limits_ff"]
    data = {"schema_version": "upper-repeaters/1", "units": "dbu", "dbu_per_micron": DBU,
            "native_keepouts": blocks, "electrical": electrical, "repeaters": []}
    names = {name: i for i, name in enumerate(sorted(nets))}
    routes = {f"segment/{names[name]}/0": route for name, route in direct["routes"].items()}
    failures = dict(direct["failed"])
    allocations = {name: None for name in direct["routes"]}
    dloads = {name: [estimated_load(nets[name], route, limits, caps, electrical)]
              for name, route in direct["routes"].items()}
    rloads = dict(dloads)
    overloaded = sorted((name for name in dloads if dloads[name][0]["over_ff"] > 0),
                        key=lambda name: (-dloads[name][0]["over_ff"], name))
    # Cover separately the two diagnosed cases. A failed geometry attempt has no measured load.
    singles_failed = [name for name in sorted(failures) if len(nets[name]["sinks"]) == 1][:max_targets]
    singles_over = [name for name in overloaded if len(nets[name]["sinks"]) == 1][:max_targets]
    unavailable = {p for rectangles in spec["pins"].values() for p in access_points(rectangles, spec["technology"])}
    reserve, evidence = set(), []
    for name in singles_failed + singles_over:
        net = nets[name]
        key = f"segment/{names[name]}/0"
        fixed = area(spec, routes, omit=key)
        trial_rows = []
        committed = None
        for _, a, z, ratios in rank_sites(net, spec, blocks, unavailable, model, limits[net["driver"]],
                                         len(net["sinks"]), name in failures, reserve)[:candidate_count]:
            relay = make_relay(a, z, model)
            pick = {"repeater": relay["id"], "sinks": net["sinks"]}
            parts = physical_nets(net, names[name], pick, {relay["id"]: relay})
            pins = dict(spec["pins"])
            pins.update({relay[side]["id"]: relay[side]["m10"] for side in ("input", "output")})
            augmented = dict(spec, pins=pins)
            native = NativePins(augmented)
            trial = fixed.fork()
            segment_routes, loads = {}, []
            reason = None
            for part in parts:
                wire, reason, _, _ = search.route_net(part, augmented, trial, {}, budget, native)
                if wire is None:
                    break
                segment_routes[part["id"]] = compact(wire, part, augmented)
                loads.append(estimated_load(part, wire, {**limits, relay["output"]["id"]: model["relay_limit_ff"]},
                                            {**caps, relay["input"]["id"]: model["relay_cap_ff"]}, electrical))
            trial_rows.append({"relay": relay["id"], "input_xy_dbu": a, "output_xy_dbu": z,
                               "screen_ratios": ratios, "reason": reason, "loads": loads,
                               "wire_um": [length(r)/DBU for r in segment_routes.values()]})
            if reason:
                continue
            score = (sum(row["over_ff"] > 0 for row in loads), sum(row["over_ff"] for row in loads),
                     sum(length(route) for route in segment_routes.values()))
            if name in dloads:
                before = dloads[name][0]["over_ff"]
                if score[:2] >= (1, before):
                    continue
            if committed is None or score < committed[0]:
                committed = score, relay, pick, segment_routes, loads
            if score[0] == 0:
                break
        if committed:
            _, relay, pick, segments, loads = committed
            routes.pop(key, None)
            routes.update(segments)
            failures.pop(name, None)
            allocations[name], rloads[name] = pick, loads
            reserve.add(tuple(next(row["input_xy_dbu"] for row in trial_rows if row["relay"] == relay["id"])))
            data["repeaters"].append(relay)
        evidence.append({"net": name, "reason": "load" if name in dloads else "geometry",
                         "direct_load": dloads.get(name), "trials": trial_rows,
                         "selected": committed[1]["id"] if committed else None})
        print("repair", len(evidence), name, evidence[-1]["selected"], round(monotonic() - phase), flush=True)
    physical = projection(spec, data, allocations, failures)
    present = geometry_result(physical, routes, {f"segment/{names[n]}/0": reason for n, reason in failures.items()})
    result = {
        "schema_version": "upper-repeater-result/1", "allocations": allocations, "failed": failures,
        "physical_spec": physical, "physical_routes": present, "status": present["status"],
        "physical_qualified": False, "used_virtual": sorted(r["id"] for r in data["repeaters"]),
    }
    result["geometry_check"] = check_allocations(spec, data, result)
    return result, data, dloads, rloads, evidence


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("handoff", type=Path)
    parser.add_argument("liberty", type=Path)
    parser.add_argument("out", type=Path)
    parser.add_argument("--budget", type=int, default=2600)
    parser.add_argument("--repair-budget", type=int, default=3200)
    parser.add_argument("--rounds", type=int, default=1)
    parser.add_argument("--max-targets", type=int, default=8)
    parser.add_argument("--candidates", type=int, default=6)
    parser.add_argument("--direct", type=Path)
    parser.add_argument("--weight", type=int, default=1)
    parser.add_argument("--reserve-access", action="store_true")
    parser.add_argument("--jumps", action="store_true")
    args = parser.parse_args()
    weighted.enable(args.weight, args.jumps)
    spec = read(args.handoff / "algorithm2-input.json")
    receipt = verify_handoff(spec, args.handoff)
    args.out.mkdir()
    with (args.handoff / "nets.tsv").open(encoding="utf-8") as stream:
        families = {row["net_id"]: row["family"] for row in csv.DictReader(stream, delimiter="\t")}
    direct = read(args.direct) if args.direct else baseline(spec, args.rounds, args.budget, args.reserve_access)
    direct["geometry_check"] = verify(spec, direct)
    write(args.out / "direct.json", direct)
    model = load_model(args.liberty.read_text(), spec)
    blocks = list(read(args.handoff.parent / "placement.json")["boxes_dbu"].values())
    result, data, before, after, trials = repair(spec, direct, blocks, model, args.repair_budget,
                                                args.max_targets, args.candidates)
    write(args.out / "repair.json", result)
    write(args.out / "inventory.json", data)
    write(args.out / "trials.json", trials)
    indices = {name: i for i, name in enumerate(sorted(families))}
    logical_routes = [name for name in indices if f"segment/{indices[name]}/0" in result["physical_routes"]["routes"]]
    summary = {
        "handoff": receipt, "model": model, "source_cell": SOURCE, "sink_cell": RECEIVER, "relay_cell": REPEATER,
        "method": {key: value for key, value in vars(args).items() if isinstance(value, int)},
        "direct": {**direct["geometry_check"], "families": family_stats(families, direct["failed"], direct["routes"], before)},
        "repair": {**result["geometry_check"], "families": family_stats(families, result["failed"], logical_routes, after)},
        "tried": len(trials), "trials_with_relay": sum(row["selected"] is not None for row in trials),
        "geometric_recoveries": sum(row["selected"] is not None and row["reason"] == "geometry" for row in trials),
    }
    write(args.out / "summary.json", summary)
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
