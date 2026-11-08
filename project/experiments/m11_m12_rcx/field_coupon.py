"""Apply the held-out-qualified field extractor to the exact #194 coupon."""
import argparse
from collections import defaultdict
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import re
import tarfile

from coupon import ARCHIVE_SHA, DEF_SHA, TECH_SHA, pins_connected, spef_resistors
from field_extract import (HOLDOUT_SHA, Conductor, assemble, measure, readback,
                           rewrite_spef, scene, verify_readback)
from run import save, sha

VALIDATION_SHA = "e714a67d0edd8709a6c1a3bcc1c6e513b5d3677640a7102aaae84e67fa7060c5"
BASELINE_SHA = "86eecb840126326b88a7364451a2b8ab6b543eadc4ac3ba1affb178727c35212"
ROUTE_SHA = "1a06a73332e199bc598b80c94d495af07588ff1761997d43ffdfed71f9b05329"
Z = {10: (10.09, 12.09), 11: (12.89, 14.89), 12: (15.69, 17.69),
     110: (12.09, 12.89), 111: (14.89, 15.69)}
HALF = 2000
DBU = 2000


def layout(archive):
    assert sha(archive) == ARCHIVE_SHA
    with tarfile.open(archive, "r:gz") as bundle:
        def member(name):
            return bundle.extractfile(name).read()
        source = "escape-97881-30/"
        audit = "gds-97924-30/"
        route = member(source + "escape-2.json")
        assert sha256(route).hexdigest() == ROUTE_SHA
        proof = json.loads(member(audit + "klayout-receipt.json"))
        assert proof["passed"] and proof["nets"] == 296
        assert sha256(member(audit + "upper-only.gds")).hexdigest() == proof["sha256"]
        assert json.loads(route) == json.loads(member(audit + "route.json"))
        return json.loads(route), json.loads(member(source + "inputs.json")), proof["sha256"]


def path_order(edges, first):
    adjacent = defaultdict(list)
    for a, b, r in edges:
        assert a != b and r > 0
        adjacent[a].append((b, r))
        adjacent[b].append((a, r))
    assert all(1 <= len(v) <= 2 for v in adjacent.values())
    assert len(adjacent[first]) == 1
    nodes, resistances = [first], []
    for _ in edges:
        forward = [(n, r) for n, r in adjacent[nodes[-1]] if len(nodes) < 2 or n != nodes[-2]]
        assert len(forward) == 1
        node, r = forward[0]
        nodes.append(node)
        resistances.append(r)
    assert len(set(nodes)) == len(nodes) == len(adjacent)
    return nodes, resistances


def box(layer, a, b):
    x0, x1 = sorted((a[0], b[0]))
    y0, y1 = sorted((a[1], b[1]))
    z0, z1 = Z[layer]
    return ((x0 - HALF) / DBU, (y0 - HALF) / DBU, z0,
            (x1 + HALF) / DBU, (y1 + HALF) / DBU, z1)


def geometry(name, route, rects, graph, terminal_order):
    boxes, edges = set(), []
    for layer, a, b in route["segments"]:
        boxes.add(box(layer, a, b))
        length = (abs(a[0] - b[0]) + abs(a[1] - b[1])) / DBU
        if length:
            # DEF uses default half-width extension at each end.
            edges.append(((layer, *a), (layer, *b), 0.03 * (length / 2 + 1)))
    for layer in (10, 11):
        for p in route[f"via{layer}"]:
            for level in (layer, layer + 100, layer + 1):
                boxes.add(box(level, p, p))
            edges.append(((layer, *p), (layer + 1, *p), 0.08))
    starts = []
    for x0, y0, x1, y1 in rects:
        possible = [(10, x, y) for x, y in route["via10"]
                    if x0 <= x - HALF and x + HALF <= x1
                    and y0 <= y - HALF and y + HALF <= y1]
        assert len(possible) == 1, (name, rects)
        starts += possible
    physical, nominal = path_order(edges, starts[0])
    if len(starts) == 2:
        assert physical[-1] == starts[-1]
    else:
        assert name.endswith("_ready") and physical[-1][0] == 11
    labels, actual = path_order(graph["resistors"], terminal_order[0])
    assert labels[-1] == terminal_order[-1] and len(labels) == len(physical)
    assert all(math.isclose(a, b, rel_tol=5e-6, abs_tol=1e-7)
               for a, b in zip(nominal, actual)), (name, nominal, actual)
    nodes = {label: (x / DBU, y / DBU, sum(Z[layer]) / 2)
             for label, (layer, x, y) in zip(labels, physical)}
    return Conductor(name, sorted(boxes), nodes)


def overlaps(routes):
    horizontal, vertical = [], []
    for net, route in routes.items():
        for layer, a, b in route["segments"]:
            if a != b:
                rect = box(layer, a, b)
                (horizontal if layer == 11 else vertical).append((net, rect))
    return {tuple(sorted((a, b))) for a, h in horizontal for b, v in vertical if a != b
            and max(h[0], v[0]) < min(h[3], v[3])
            and max(h[1], v[1]) < min(h[4], v[4])}


def coupon(out, fit, approved, base, archive, cpus):
    validation = approved / "result/validation.json"
    assert sha(validation) == VALIDATION_SHA
    gate = json.loads(validation.read_text())
    assert gate["passed"] and gate["original_report_sha256"] == HOLDOUT_SHA
    assert len(gate["results"]) == 14 and all(all(row["checks"].values()) for row in gate["results"])
    binary = approved / "field_row"
    assert sha(binary) == gate["solver_sha256"]
    tech = fit / "patterns/overlay/research12.tech.lef"
    design = base / "escape-2.def"
    baseline = base / "extracted.spef"
    assert sha(tech) == TECH_SHA and sha(design) == DEF_SHA and sha(baseline) == BASELINE_SHA
    lefs = [base / f"{name}.lef" for name in "PUCFJ"]
    base_report = json.loads((base / "summary.json").read_text())
    assert base_report["resistor_graph_connected"] == 296
    assert all(sha(path) == base_report["lef_sha256"][path.name] for path in lefs)
    route_data, layout_data, gds_sha = layout(archive)
    assert not route_data["failed"]
    routes = route_data["routes"]
    graph = spef_resistors(baseline)
    assert set(routes) == set(graph) and len(routes) == 296
    names = dict(re.findall(r"(?m)^(\*\d+) ([^\s]+)\s*$",
                            baseline.read_text().split("*NAME_MAP\n", 1)[1].split("*PORTS\n", 1)[0]))
    terminals = {net: [(a if a != "PIN" else "", b) for a, b in [(i, p), (j, q)]]
                 for net, i, p, j, q in re.findall(
                     r"(?m)^- (\S+) \( (\S+) (\S+) \) \( (\S+) (\S+) \) \+ USE SIGNAL",
                     design.read_text().split("\nNETS ", 1)[1])}
    nets = []
    for net in sorted(routes):
        assert pins_connected(graph[net])
        labels = {}
        for alias in graph[net]["pins"]:
            prefix, sep, pin = alias.partition(":")
            key = (names[prefix], pin) if sep else ("", names.get(prefix, prefix))
            labels[key] = alias
        order = [labels[pair] for pair in terminals[net]]
        nets.append(geometry(net, routes[net], layout_data["macro_endpoint_rects_dbu"][net],
                             graph[net], order))
    model = out / "field.in"
    scene(model, nets)
    save(out / "geometry.json", dict(
        net_count=len(nets), boxes=sum(len(n.boxes) for n in nets),
        resistor_nodes=sum(len(n.nodes) for n in nets), netlist_sha256=sha(model),
        pr194_upper_gds_sha256=gds_sha, baseline_spef_sha256=BASELINE_SHA,
        boundary="M10 landing squares, #194 upper metal and vias, dielectric over ground plane"))
    print("Bound all 296 routed conductor and resistor graphs", flush=True)
    rows = measure([(model, i) for i in range(len(nets))], binary, cpus, 1 << 18)
    ground, coupling, diagnostics = assemble(nets, rows)
    corrected = out / "field.spef"
    rewrite_spef(baseline, corrected, ground, coupling)
    totals, mutual = readback(out, tech, design, corrected, lefs)
    verify_readback(totals, mutual, ground, coupling)
    assert all(abs(totals[n][0] - sum(edge[2] for edge in graph[n]["resistors"]))
               <= 1e-5 * max(1, totals[n][0]) for n in graph)
    crossings = overlaps(routes)
    missing = sorted(crossings - set(mutual))
    result = dict(passed=not missing, verified_holdout_sha256=VALIDATION_SHA,
                  solver_sha256=gate["solver_sha256"], net_count=len(totals),
                  resistance_graphs_preserved=len(graph), coupled_net_pairs=len(mutual),
                  coupled_node_pairs=sum(map(len, coupling.values())),
                  projected_crossing_net_pairs=len(crossings),
                  crossing_pairs_with_nonzero_coupling=len(crossings) - len(missing),
                  missing_crossing_pairs=missing, field_spef_sha256=sha(corrected),
                  total_ground_ff=sum(row[1] for row in totals.values()),
                  total_coupling_ff=sum(mutual.values()), diagnostics=diagnostics)
    save(out / "coupon-validation.json", result)
    assert not missing, "A geometrically crossing net pair had zero measured coupling"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("out", "fit", "approved", "base", "archive"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir()
    coupon(out, args.fit, args.approved, args.base, args.archive,
           int(os.environ["SLURM_CPUS_PER_TASK"]))


if __name__ == "__main__":
    main()
