"""Recover metallic connectivity from the full frozen GDS, including submacros.

Executed by KLayout in an allocated worker. Device/poly capacitances are outside
the M1--M10 conductor model; no routing OBS or macro bounding boxes are metal.
"""
import hashlib
import json
import os
from pathlib import Path
import time
import pya


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for b in iter(lambda: stream.read(4 << 20), b""):
            h.update(b)
    return h.hexdigest()


def register(l2n, region, name):
    l2n.register(region, name)
    return l2n.layer_by_name(name)


def control():
    l2n = pya.LayoutToNetlist("CONTROL", 0.001)
    a, via, b = pya.Region(), pya.Region(), pya.Region()
    a.insert(pya.Box(0, 0, 1000, 1000))
    a.insert(pya.Box(3000, 0, 4000, 1000))
    via.insert(pya.Box(400, 400, 600, 600))
    b.insert(pya.Box(0, 0, 2000, 1000))
    a = register(l2n, a, "a")
    via = register(l2n, via, "via")
    b = register(l2n, b, "b")
    for r in (a, via, b):
        l2n.connect(r)
    l2n.connect(a, via)
    l2n.connect(via, b)
    l2n.extract_netlist()
    n = l2n.probe_net(a, pya.DPoint(0.5, 0.5))
    linked = l2n.probe_net(b, pya.DPoint(1.5, 0.5))
    other = l2n.probe_net(a, pya.DPoint(3.5, 0.5))
    assert n is not None and n.cluster_id == linked.cluster_id
    assert other is not None and n.cluster_id != other.cluster_id
    assert l2n.shapes_of_net(n, a).area() == 1000000
    return dict(passed=True, connected_via=True, isolated_conductor=True)


def main():
    out = Path(os.environ["COUPLING_TOPOLOGY_OUT"])
    out.mkdir()
    started = time.monotonic()
    controls = control()
    receipt = Path("/public/home/yuzelu/PingyangHuang/issue-215-top-pex-zOz2uxIr/route-206.json")
    refs = json.loads(receipt.read_text())
    kinds = ("C0", "F0", "J0", "P0", "T0", "U0")
    kind = kinds[int(os.environ["COUPLING_TOPOLOGY_INDEX"])]
    ref = refs["native_masks"][kind]
    gds = Path(ref["path"])
    assert sha(gds) == ref["sha256"]
    print("READ_GDS", kind, str(gds), flush=True)
    layout = pya.Layout()
    layout.read(str(gds))
    top = layout.top_cell()
    hierarchical = os.environ.get("COUPLING_TOPOLOGY_HIERARCHICAL", "1") == "1"
    l2n = (pya.LayoutToNetlist(top.begin_shapes_rec(layout.layer(11, 0)))
           if hierarchical else pya.LayoutToNetlist("NATIVE_" + kind, layout.dbu))
    l2n.threads = int(os.environ["COUPLING_THREADS"])
    regions, counts = {}, {}
    # Native mapping is checked against the unchanged platform .lyt.
    platform = Path("/OpenROAD-flow-scripts/flow/platforms/nangate45/FreePDK45.lyt")
    assert platform.is_file(), str(platform)
    import re
    mapping = {n: (int(a), int(b)) for n, a, b in re.findall(
        r"'([^']+)\s+:\s+(\d+)/(\d+)'", platform.read_text())}
    for i in range(1, 11):
        assert mapping["metal" + str(i)] == (9 + 2 * i, 0)
    for i in range(1, 10):
        assert mapping["via" + str(i)] == (10 + 2 * i, 0)
    for name in ["metal" + str(i) for i in range(1, 11)] + ["via" + str(i) for i in range(1, 10)]:
        index = layout.find_layer(*mapping[name])
        if hierarchical:
            regions[name] = (l2n.make_polygon_layer(index, name) if index is not None
                             else l2n.make_layer(name))
            counts[name] = regions[name].count()
        else:
            raw = pya.Region(top.begin_shapes_rec(index)) if index is not None else pya.Region()
            counts[name] = raw.count()
            regions[name] = register(l2n, raw, name)
        l2n.connect(regions[name])
        print("LAYER", name, counts[name], flush=True)
    for i in range(1, 10):
        l2n.connect(regions["metal" + str(i)], regions["via" + str(i)])
        l2n.connect(regions["via" + str(i)], regions["metal" + str(i + 1)])
    print("EXTRACT_CONNECTIVITY", flush=True)
    l2n.extract_netlist()
    circuits = list(l2n.netlist().each_circuit())
    roots = [c for c in circuits if c.name == (top.name if hierarchical else "NATIVE_" + kind)]
    assert len(roots) == 1, "Unambiguous physical top circuit required"
    net_count = sum(1 for _ in roots[0].each_net())
    print("NETS", net_count, flush=True)
    database = out / "native.l2n"
    # Persist before interface checks, so a failed check can be investigated
    # without repeating the expensive extraction.
    l2n.write(str(database))
    print("TOPOLOGY_SAVED", str(database), flush=True)
    power = {}
    for i in range(1, 11):
        index = layout.find_layer(*mapping["metal" + str(i)])
        if index is None:
            continue
        for shape in top.shapes(index).each():
            if shape.is_text() and shape.text.string in ("VDD", "VSS"):
                net = l2n.probe_net(regions["metal" + str(i)], shape.text.trans.disp)
                if net is not None:
                    power.setdefault(shape.text.string, set()).add(int(net.cluster_id))
    print("POWER", {k: sorted(v) for k, v in power.items()}, flush=True)
    probes = {}
    base = Path(refs["artifacts"]["inputs.json"]["path"])
    binding = json.loads(Path(refs["artifacts"]["case-binding.json"]["path"]).read_text())
    rects = json.loads(base.read_text())["macro_endpoint_rects_dbu"]
    for word, ends in binding["endpoints"].items():
        for endpoint, rect in zip(ends, rects[word]):
            instance, pin = endpoint
            if instance[0] != kind[0]:
                continue
            x, y = refs["positions_um"][instance]
            point = pya.DPoint((rect[0] + rect[2]) / 4000 - x,
                               (rect[1] + rect[3]) / 4000 - y)
            net = l2n.probe_net(regions["metal10"], point)
            assert net is not None, (instance, pin, str(point))
            old = probes.setdefault(pin, dict(cluster=int(net.cluster_id), point_um=[point.x, point.y]))
            assert old["cluster"] == int(net.cluster_id), (instance, pin)
    result = dict(kind=kind, source_gds=ref, dbu=layout.dbu,
                  layout_to_netlist_controls=controls, shape_counts=counts,
                  top_circuit_nets=net_count, hierarchical_circuits=len(circuits),
                  root_circuit_name=roots[0].name, hierarchical=hierarchical,
                  boundary_probes=probes,
                  power_clusters={k: sorted(v) for k,v in power.items()},
                  database_bytes=database.stat().st_size, database_sha256=sha(database),
                  elapsed_seconds=time.monotonic() - started,
                  scope="Exact M1--M10/via1--via9 GDS polygons and physical metal connectivity, including nested cells. Device/poly conductors are outside this model.")
    assert sha(gds) == ref["sha256"]
    (out / "topology.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k:v for k,v in result.items() if k != "boundary_probes"}), flush=True)


main()
