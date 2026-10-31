"""One fixed full-interface plan: four sides, two staggered via columns.

The demo stack retains width/spacing2um, via cut2um/spacing2.2um and4um grid.
Successive4um wire tracks alternate their via by4um: cuts are diagonal rather
than illegal4um collinear cuts. Native M10 landings remain2x2um and internal.
This planner is not physical acceptance; actual native/GDS/RC gates are separate.
"""
import math
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "block_v1"))
from revision300_geometry import DBU, u, box, verify


def generate(ports, side, technology):
    g = technology["geometry_um"]
    assert (g["pitch"], g["cut_width"], g["cut_spacing"]) == (4., 2., 2.2)
    ox, oy, step, width = u(g["track_offset_x"]), u(g["track_offset_y"]), u(4), u(side)
    def near(value, offset):
        return offset + step * round((value-offset)/step)
    xl, xr = near(width/4, ox), near(3*width/4, ox)
    yb, yt = near(width/4, oy), near(3*width/4, oy)
    xs = list(range(ox + step*math.ceil((u(24)-ox)/step), width-u(24), step))
    # Exclude both rows of vertical via landings, including their cut spacing.
    ys = [y for y in range(oy + step*math.ceil((u(24)-oy)/step), width-u(24), step)
          if all(abs(y-v) >= u(8) for v in (yb, yb+step, yt, yt-step))]
    slots = dict(left=ys, right=ys, bottom=xs, top=xs)
    used = {name: 0 for name in slots}
    pins, shapes, connections, groups = [], [], [], []
    def add(layer, rectangle, net):
        shapes.append(dict(layer=layer, box_dbu=list(map(int, rectangle)), net=net))
    def wire(layer, a, b, net):
        assert a[0] == b[0] or a[1] == b[1]
        add(layer, [min(a[0],b[0])-u(1), min(a[1],b[1])-u(1),
                    max(a[0],b[0])+u(1), max(a[1],b[1])+u(1)], net)
    for port, entry in sorted(ports.items()):
        count = entry["bits"]
        assert count > 0 and entry["direction"] in ("input", "output")
        for begin in range(0, count, 16):
            n = min(16, count-begin)
            available = [s for s in slots if used[s]+n <= len(slots[s])]
            assert available, ("Insufficient staggered interface tracks", side, port, used)
            direction = min(available, key=lambda s: (used[s]/len(slots[s]), list(slots).index(s)))
            group = f"{port}-{begin//16}"
            groups.append(dict(id=group, port=port, first=begin, bits=n, side=direction))
            for i in range(begin, begin+n):
                track = slots[direction][used[direction]]
                # Use the real4um grid parity, including any excluded rows.
                parity = ((track-(oy if direction in ("left","right") else ox))//step) % 2
                used[direction] += 1
                if direction in ("left", "right"):
                    x, y = (xl+parity*step if direction == "left" else xr-parity*step), track
                    end = [ox-u(32) if direction == "left" else ox+step*math.ceil(width/step)+u(32), y]
                    layer = "metal11"
                else:
                    x, y = track, (yb+parity*step if direction == "bottom" else yt-parity*step)
                    end = [x, oy-u(32) if direction == "bottom" else oy+step*math.ceil(width/step)+u(32)]
                    layer = "metal12"
                name = port if count == 1 else f"{port}[{i}]"
                pins.append(dict(pin=name, port=port, index=i, direction=entry["direction"],
                                 role="clock" if port == "clk" else "signal", layer="metal10",
                                 xy_um=[x/DBU, y/DBU], size_um=[2.,2.], region="internal",
                                 group=group, escape_side=direction))
                add("metal10", box(x,y), name)
                add("via10", box(x,y), name)
                if layer == "metal12":
                    add("metal11", box(x,y), name)
                    add("via11", box(x,y), name)
                wire(layer, [x,y], end, name)
                connections.append(dict(net=name, source_m10_dbu=[x,y],
                                        external_endpoint_dbu=end, endpoint_layer=layer))
    fixture = dict(schema="coarse-interface-fixture/1", name="all-ports", dbu_per_um=DBU,
                   expected_bits=len(pins), macro_box_dbu=[0,0,width,width],
                   test_boundary_dbu=[-u(40),-u(40),width+u(40),width+u(40)],
                   ports=connections, shapes=shapes)
    proof = verify(fixture, technology)
    plan = dict(schema="block-v1-pin-plan/1", policy="four-sides-staggered-via-v1",
                pins=pins, ports=len(pins), internal_ports=len(pins), groups=groups,
                track_demand=used, track_capacity={s:len(v) for s,v in slots.items()},
                wire_pitch_um=4., stagger_um=4., qualified_access=False,
                scope="One declared candidate; unchanged coarse rules. Actual native route, full GDS, drive/RC and timing still required.")
    return plan, fixture, proof
