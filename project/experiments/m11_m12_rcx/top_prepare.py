"""Bind the frozen #206 layout to the #202 field and resistance contract."""
import argparse
from collections import defaultdict
from dataclasses import asdict
import json
from pathlib import Path
import re

from coupon import TECH_SHA, spef_resistors
from field_coupon import VALIDATION_SHA, Z, geometry, overlaps
from field_extract import RULES_SHA, scene
from run import openroad, save, sha

ROUTE_SHA = "a140e85e17cf9827b245fea3393cb85c3fad36dd99a8a09957e59f21ee6dfc1b"
COUNT = 2491


def checked_file(record):
    path = Path(record["path"])
    assert path.stat().st_size == record["bytes"] and sha(path) == record["sha256"], path
    return path


def odb_rectangles(path):
    levels = {"metal10": 10, "metal11": 11, "metal12": 12, "via10": 110, "via11": 111}
    rectangles = defaultdict(set)
    with path.open() as stream:
        assert next(stream).strip().endswith("dbu_per_um=2000")
        aliases = {}
        for line in stream:
            if line.startswith("# NET "):
                _, _, alias, name = line.split()
                aliases[alias] = bytes.fromhex(name).decode()
                continue
            alias, layer, kind, *xy = line.split()
            if kind == "instance-pin":
                continue
            assert kind in ("wire", "wire-via") and layer in levels
            assert layer != "metal10" or kind == "wire-via"
            level = levels[layer]
            x0, y0, x1, y1 = (int(v) / 2000 for v in xy)
            z0, z1 = Z[level]
            rectangles[aliases[alias]].add((x0, y0, z0, x1, y1, z1))
    return rectangles


def prepare(out, receipt_path, rules, accepted):
    assert sha(rules) == RULES_SHA
    assert sha(accepted / "result/validation.json") == VALIDATION_SHA
    validation = json.loads((accepted / "result/validation.json").read_text())
    assert validation["passed"] and len(validation["results"]) == 14
    assert sha(accepted / "field_row") == validation["solver_sha256"]
    receipt = json.loads(receipt_path.read_text())
    assert receipt["validation"]["routed_nets"] == receipt["validation"]["odb_reached_nets"] == COUNT
    assert receipt["validation"]["geometry_errors"] == 0
    assert all(receipt["validation"]["gds_checks"].values())
    refs = receipt["artifacts"]
    paths = {k: checked_file(refs[k]) for k in
             ("route.def", "routed.odb", "upper-only.gds", "case-binding.json",
              "inputs.json", "route-audit.json", "klayout-receipt.json")}
    tech = checked_file(receipt["research_tech_lef"])
    assert sha(tech) == TECH_SHA
    assert json.loads(checked_file(receipt["independent_odb_check"]).read_text())["passed"]
    route_file = paths["route.def"].with_name("route.json")
    assert sha(route_file) == ROUTE_SHA
    route = json.loads(route_file.read_text())
    assert not route["failed"] and len(route["routes"]) == COUNT
    endpoints = json.loads(paths["case-binding.json"].read_text())["endpoints"]
    pin_rects = json.loads(paths["inputs.json"].read_text())["macro_endpoint_rects_dbu"]
    actual_rects = odb_rectangles(checked_file(receipt["odb_exported_geometry"]))

    openroad(out, "resistance.tcl", f"""read_db {{{paths['routed.odb']}}}
set_extraction_rules_file {{{rules}}}
define_process_corner -ext_model_index 0 research
extract_parasitics -context_depth 3 -coupling_threshold 0.000001 -max_res 0 -no_merge_via_res
write_spef resistance.spef
""")
    baseline = out / "resistance.spef"
    graph = spef_resistors(baseline)
    aliases = dict(re.findall(r"(?m)^(\*\d+) ([^\s]+)\s*$",
                              baseline.read_text().split("*NAME_MAP\n", 1)[1].split("*D_NET ", 1)[0]))
    assert set(graph) == set(route["routes"]) == set(actual_rects) == set(endpoints) == set(pin_rects)
    nets = []
    for name, wires in sorted(route["routes"].items()):
        assert len(wires["via10"]) == 2
        labels = {}
        for label in graph[name]["pins"]:
            inst, pin = label.split(":", 1)
            labels[aliases[inst], pin] = label
        order = [labels[tuple(terminal)] for terminal in endpoints[name]]
        net = geometry(name, wires, pin_rects[name], graph[name], order)
        assert set(net.boxes) == actual_rects[name], (name, set(net.boxes) ^ actual_rects[name])
        nets.append(net)

    field = out / "field.in"
    scene(field, nets)
    save(out / "conductors.json", [asdict(net) for net in nets])
    crossing = sorted(overlaps(route["routes"]))
    save(out / "crossings.json", crossing)
    result = dict(passed=True, net_count=len(nets), exact_odb_rectangle_nets=len(nets),
                  resistor_nodes=sum(len(net.nodes) for net in nets),
                  resistor_edges=sum(len(record["resistors"]) for record in graph.values()),
                  boxes=sum(len(net.boxes) for net in nets), projected_crossings=len(crossing),
                  field_sha256=sha(field), conductors_sha256=sha(out / "conductors.json"),
                  crossings_sha256=sha(out / "crossings.json"), resistance_sha256=sha(baseline),
                  receipt_sha256=sha(receipt_path), solver_sha256=validation["solver_sha256"])
    save(out / "geometry.json", result)
    print(json.dumps(result), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("out", "receipt", "rules", "accepted"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir()
    prepare(args.out, args.receipt, args.rules, args.accepted)
