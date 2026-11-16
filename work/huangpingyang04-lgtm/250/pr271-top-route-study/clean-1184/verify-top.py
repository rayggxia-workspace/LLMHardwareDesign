"""Bridge the compiled routing experiment to Algo2's JSON and strict verifier."""
import argparse
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path

from check import digest, verify
from geometry import NativePins, Occupancy, access_points, via_shapes
from handoff import verify_handoff

parser = argparse.ArgumentParser()
parser.add_argument("mode", choices=("export", "verify"))
parser.add_argument("input", type=Path)
parser.add_argument("network", type=Path)
parser.add_argument("output", type=Path, nargs="?")
parser.add_argument("--original", type=Path, required=True)
parser.add_argument("--escape", type=Path, required=True)
args = parser.parse_args()
raw = args.input.read_bytes()
spec = json.loads(raw)
origin_raw = args.original.read_bytes()
source = json.loads(origin_raw)
admission = verify_handoff(source, args.original.parent)
original_sha = hashlib.sha256(origin_raw).hexdigest()
assert original_sha == "8c75c87d1875e34d6c3fe1bfa8a98611408e2d179e293432d6c0806516c401b4"
escape_raw = args.escape.read_bytes()
escape = json.loads(escape_raw)
overlay_sha = hashlib.sha256(escape_raw).hexdigest()
assert escape["original_handoff_sha256"] == "31ffb0b6e7ec5fc05b39bc93b340f892cb2b99097a01a24f8f4f3e24ba9115e8"
assert spec["context"] == dict(source["context"], lower_escape_overlay_sha256=overlay_sha)
for key in ("nets", "technology", "obstacles", "units", "schema_version"):
    assert spec[key] == source[key]
pins = dict(source["pins"])
ids = {net["id"]: net for net in source["nets"]}
overlay_ids = set()
overlay_pins = set()
for change in escape["rebound"]:
    nid, pin = change["net"], change["pin"]
    net = ids[nid]
    assert pin not in overlay_pins and pin.split("/")[0] in {"sw","U0","C0","dma","P0","P1","P2","mc"}
    overlay_pins.add(pin)
    assert pin in (net["driver"], *net["sinks"])
    assert pins[pin] == [change["old_m10"]]
    pins["frozen_escape_source/" + pin] = pins[pin]
    pins[pin] = [change["new_m10"]]
    overlay_ids.add(nid)
assert len(overlay_ids) == escape["route_count"] and spec["pins"] == pins
assert len(overlay_pins) == escape["endpoint_count"]
tech = spec["technology"]
nets = spec["nets"]
with (args.original.parent/"nets.tsv").open() as source:
    family = {r["net_id"]: r["family"] for r in csv.DictReader(source, delimiter="\t")}
assert Counter(family.values()) == {"packet": 1031, "decode.index.transport": 153}
assert len(nets) == 1184 and set(family) == {net["id"] for net in nets}
step = tech["access_pitch"]
ox, oy = tech["origin"]
radius = tech["access_radius"]
assert tech["pitch"] == 21*step and tech["width"] == 10*step and tech["spacing"] == 10*step
assert not spec["obstacles"]
for kind, spacing in (("via10", 10), ("via11", 11)):
    rule = tech[kind]
    assert rule == dict(cut=10*step, spacing=spacing*step, lower_enclosure=0, upper_enclosure=0)
pins_by_net = [[net["driver"], *net["sinks"]] for net in nets]
landings = {}
native = NativePins(spec)
fixed = Occupancy(tech)
for net, pins in zip(nets, pins_by_net):
    for pin in pins:
        points = [p for p in access_points(spec["pins"][pin], tech) if native.exclusive(p, set(pins))]
        point, = points
        landing = via_shapes("via10", point, tech)
        assert fixed.legal(landing, net["id"]), (pin, point)
        fixed.add(landing, net["id"])
        landings[pin] = point

def lattice(x, offset, round_up=False):
    return (x-offset+(step-1 if round_up else 0))//step

if args.mode == "export":
    l, b, r, t = tech["bounds"]
    margin = tech["width"]//2
    with args.network.open("x") as out:
        print(lattice(l+margin,ox,True), lattice(b+margin,oy,True),
              lattice(r-margin,ox), lattice(t-margin,oy), len(nets), file=out)
        for i, pins in enumerate(pins_by_net):
            windows = [rect for pin in pins for rect in spec["pins"][pin]]
            print(i,len(pins),len(windows),file=out)
            for pin in pins:
                x, y = landings[pin]
                print(lattice(x,ox),lattice(y,oy),file=out)
            for l, b, r, t in windows:
                print(lattice(l-radius,ox,True),lattice(b-radius,oy,True),
                      lattice(r+radius,ox),lattice(t+radius,oy),file=out)
else:
    routes = {}
    coord = lambda x, y: [x*step+ox,y*step+oy]
    with args.network.open() as inp:
        while True:
            line = inp.readline()
            if not line:
                break
            index, n_wires, n_vias = map(int, line.split())
            name = nets[index]["id"]
            assert name not in routes
            segments = []
            for _ in range(n_wires):
                xa, ya, xb, yb, layer = map(int, inp.readline().split())
                segments.append(dict(a=coord(xa,ya),b=coord(xb,yb),layer="M"+str(layer+11)))
            via11 = [coord(*map(int,inp.readline().split())) for _ in range(n_vias)]
            via10 = [dict(pin=pin,at=list(landings[pin])) for pin in pins_by_net[index]]
            routes[name] = dict(segments=segments,via10=via10,via11=via11)
    failed = {n: "search_not_found" for n in family if n not in routes}
    result = dict(schema_version="upper-router-result/1",routes=routes,failed=failed,
                  status="partial" if failed else "geometry_complete",physical_qualified=False,
                  electrical_status="not_evaluated",timing_status="not_evaluated",
                  context=spec["context"],spec_sha256=digest(spec))
    result["geometry_check"] = verify(spec,result)
    result["evidence"] = dict(handoff=admission,requested=dict(Counter(family.values())),
                              routed=dict(Counter(family[n] for n in routes)),
                              unresolved=dict(Counter(family[n] for n in failed)),
                              lower_overlay_sha256=overlay_sha,
                              through_escape=len(set(routes) & overlay_ids),
                              escape_available=len(overlay_ids))
    args.output.write_text(json.dumps(result,separators=(",",":"))+"\n")
    print(result["geometry_check"])
    print(result["evidence"])
