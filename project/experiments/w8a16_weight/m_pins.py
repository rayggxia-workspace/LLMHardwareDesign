"""Compact edge-staggered native pins under the unchanged 2um demo rules.

The old quarter-width pin bands remove central escape tracks on both axes.
This new candidate places both bands near each edge and retains diagonal
4um staggering at corners. Every emitted shape passes the original complete
geometry checker. Actual native P&R/DRC and final-ODB escape remain separate.
"""
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/"project/experiments/block_v1"))
from revision300_geometry import DBU, u, box, verify


def generate(ports, side, technology, bands=2):
    assert bands == 2 and side >= 80
    g = technology["geometry_um"]
    assert (g["pitch"], g["cut_width"], g["cut_spacing"]) == (4., 2., 2.2)
    ox, oy, step, width = u(g["track_offset_x"]), u(g["track_offset_y"]), u(4), u(side)
    near = lambda value, offset: offset + step*round((value-offset)/step)
    xl, xr = near(u(12), ox), near(width-u(12), ox)
    yb, yt = near(u(12), oy), near(width-u(12), oy)
    xs = list(range(ox+step*math.ceil((u(20)-ox)/step), width-u(16), step))
    ys = list(range(oy+step*math.ceil((u(20)-oy)/step), width-u(16), step))
    slots = dict(left=ys, right=ys, bottom=xs, top=xs)
    used = dict.fromkeys(slots, 0)
    pins, shapes, connections, groups = [], [], [], []
    def add(layer, rectangle, net):
        shapes.append(dict(layer=layer, box_dbu=list(map(int, rectangle)), net=net))
    for port, entry in sorted(ports.items()):
        count = entry["bits"]
        assert count > 0 and entry["direction"] in ("input", "output")
        for begin in range(0, count, 16):
            n = min(16, count-begin)
            available = [s for s in slots if used[s]+n <= len(slots[s])]
            assert available, ("Insufficient edge-staggered interface tracks", side, port, used)
            direction = min(available, key=lambda s: (used[s]/len(slots[s]), list(slots).index(s)))
            group = f"{port}-{begin//16}"
            groups.append(dict(id=group, port=port, first=begin, bits=n, side=direction))
            for i in range(begin, begin+n):
                track = slots[direction][used[direction]]
                band = ((track-(oy if direction in ("left", "right") else ox))//step) % 2
                used[direction] += 1
                if direction in ("left", "right"):
                    x, y = (xl+band*step if direction == "left" else xr-band*step), track
                    endpoint = [ox-u(32) if direction == "left" else ox+step*math.ceil(width/step)+u(32), y]
                    layer = "metal11"
                else:
                    x, y = track, (yb+band*step if direction == "bottom" else yt-band*step)
                    endpoint = [x, oy-u(32) if direction == "bottom" else oy+step*math.ceil(width/step)+u(32)]
                    layer = "metal12"
                name = port if count == 1 else f"{port}[{i}]"
                pins.append(dict(pin=name, port=port, index=i, direction=entry["direction"],
                    role="clock" if port == "clk" else "signal", layer="metal10", xy_um=[x/DBU,y/DBU],
                    size_um=[2.,2.], region="internal", group=group, escape_side=direction))
                add("metal10", box(x,y), name)
                add("via10", box(x,y), name)
                if layer == "metal12":
                    add("metal11", box(x,y), name)
                    add("via11", box(x,y), name)
                add(layer, [min(x,endpoint[0])-u(1),min(y,endpoint[1])-u(1),
                            max(x,endpoint[0])+u(1),max(y,endpoint[1])+u(1)], name)
                connections.append(dict(net=name, source_m10_dbu=[x,y], external_endpoint_dbu=endpoint,
                                        endpoint_layer=layer))
    fixture = dict(schema="coarse-interface-fixture/1", name="all-ports", dbu_per_um=DBU,
        expected_bits=len(pins), macro_box_dbu=[0,0,width,width],
        test_boundary_dbu=[-u(40),-u(40),width+u(40),width+u(40)], ports=connections, shapes=shapes)
    proof = verify(fixture, technology)
    plan = dict(schema="block-v1-pin-plan/1", policy="m-product-four-sides-edge-staggered-v1", pins=pins,
        ports=len(pins), internal_ports=len(pins), groups=groups, track_demand=used,
        track_capacity={s:len(v) for s,v in slots.items()}, wire_pitch_um=4., stagger_um=4.,
        qualified_access=False, scope="New native pin placement; original 2um demo rules unchanged. Actual physical and final escape gates mandatory.")
    return plan, fixture, proof
