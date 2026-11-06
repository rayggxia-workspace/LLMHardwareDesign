"""Issue 191 passive M11/M12 route coupons using accepted abstract LEFs."""
import json
import os
from pathlib import Path
import re
import sys

ROOT = Path.cwd()
index = int(sys.argv[1])
gap = (128, 256)[index % 2]
vertical = bool(index & 2)
joint = 4 <= index <= 9
isolated = index >= 8
p_only = index in (8, 9)
batch_id = os.environ.get("SLURM_ARRAY_JOB_ID", "local")
out = ROOT / f"case-{batch_id}-{index}"
out.mkdir()
sources = {kind: ROOT / f"{kind}.lef" for kind in "PUCFJ"}
masters, sizes, pins = {}, {}, {}
for kind, source in sources.items():
    lef = source.read_text()
    masters[kind] = re.search(r"^MACRO\s+(\S+)", lef, re.M)[1]
    w, h = re.search(r"^\s+SIZE\s+(\d+) BY (\d+)", lef, re.M).groups()
    sizes[kind] = int(w), int(h)
    pins[kind] = {}
    for m in re.finditer(r"^\s+PIN (\S+)\s*\n(.*?)^\s+END \1\s*$", lef, re.M | re.S):
        body = m[2]
        shape = re.search(r"LAYER metal10\s*;\s*RECT\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)", body)
        if shape:
            pins[kind][m[1]] = [round(float(val) * 2000) for val in shape.groups()]

# Offsets are aligned to both the native and research track pitches.
positions = {}
def row(names, y):
    x = gap
    for name in names:
        positions[name] = x, y
        x += sizes[name[0]][0] + gap
        x = ((x + 7) // 8) * 8

row(("P0", "P1", "P2"), gap)
middle = ((gap + 3100 + gap + 7) // 8) * 8
row(("C0", "F0" if vertical else "U0", "J0"), middle)
upper = ((middle + 2600 + gap + 7) // 8) * 8
row(("U0" if vertical else "F0", "U1", "J1"), upper)
if isolated:
    keep = ("P0",) if p_only else ("C0", "U0")
    x0 = min(positions[name][0] for name in keep) - gap
    y0 = min(positions[name][1] for name in keep) - gap
    positions = {name: (positions[name][0]-x0, positions[name][1]-y0) for name in keep}
width = max(x + sizes[name[0]][0] for name, (x, y) in positions.items()) + gap
height = max(y + sizes[name[0]][1] for name, (x, y) in positions.items()) + gap
nets, port_list, expected, guide_points, proxies = [], [], {}, {}, {}
def add(net, a, b):
    endpoints = []
    centers = []
    for name, port in (a, b):
        if name == "PIN":
            centers.append(proxies[port])
            continue
        rect = pins[name[0]][port]
        x, y = positions[name]
        endpoints.append([rect[0]+x*2000, rect[1]+y*2000, rect[2]+x*2000, rect[3]+y*2000])
        rect = endpoints[-1]
        centers.append(((rect[0]+rect[2])//2, (rect[1]+rect[3])//2))
    guide_points[net] = centers
    expected[net] = endpoints
    nets.append(f"- {net} ( {a[0]} {a[1]} ) ( {b[0]} {b[1]} ) + USE SIGNAL ;")

for a, b in (() if p_only else (("C0", "U0"), ("U0", "C0"))):
    stem = f"{a}_{b}"
    for bit in range(128):
        add(f"{stem}_data_{bit}", (a, f"tx_data[{bit}]"), (b, f"rx_data[{bit}]"))
    add(f"{stem}_valid", (a, "tx_valid"), (b, "rx_valid"))
    add(f"{stem}_stored", (b, "rx_stored"), (a, "tx_take"))
    # Parent sidecar is reserved. The ready sink is a proxy top pin, so it
    # is excluded from the count of true macro-pin terminations.
    proxy = f"{stem}_ready_proxy"
    x, y = positions[a]
    px, py = (x-24)*2000+190, (y+48)*2000+140
    proxies[proxy] = px, py
    net = f"{stem}_ready"
    port_list.append(f"- {proxy} + NET {net} + DIRECTION OUTPUT + USE SIGNAL + LAYER metal11 ( -2000 -2000 ) ( 2000 2000 ) + FIXED ( {px} {py} ) N ;")
    add(net, (b, "rx_ready"), ("PIN", proxy))
if joint:
    for bit in range(32):
        add(f"p_gate_{bit}", ("P0", f"m_to_g_data[{bit}]"), ("P0", f"g_from_m_data[{bit}]"))
    add("p_gate_valid", ("P0", "m_to_g_valid"), ("P0", "g_from_m_valid"))
    add("p_gate_take", ("P0", "g_from_m_take"), ("P0", "m_to_g_take"))

components = [f"- {name} {masters[name[0]]} + FIXED ( {x*2000} {y*2000} ) N ;" for name,(x,y) in positions.items()]
(out/"coupon.def").write_text("\n".join([
    "VERSION 5.8 ;", 'DIVIDERCHAR "/" ;', 'BUSBITCHARS "[]" ;', "DESIGN nine_block_coupon ;",
    "UNITS DISTANCE MICRONS 2000 ;", f"DIEAREA ( 0 0 ) ( {width*2000} {height*2000} ) ;",
    f"COMPONENTS {len(components)} ;", *components, "END COMPONENTS",
    f"PINS {len(port_list)} ;", *port_list, "END PINS",
    f"NETS {len(nets)} ;", *nets, "END NETS", "END DESIGN", ""
]))
(out/"inputs.json").write_text(json.dumps(dict(
    positions_um=positions, sizes_um=sizes, die_um=[width,height], clearance_setting_um=gap,
    includes_p=joint, macro_endpoint_rects_dbu=expected, control_pg_clock_implemented=False,
    transport_implemented=False, synthetic_ready_sinks=len(port_list), isolated=isolated), indent=2))
grid = 120000
def box(x1, y1, x2, y2, layer, padding=1):
    xl, xh = sorted((x1//grid, x2//grid))
    yl, yh = sorted((y1//grid, y2//grid))
    return f"{max(0, xl-padding)*grid} {max(0, yl-padding)*grid} {(xh+1+padding)*grid} {(yh+1+padding)*grid} {layer}"
guides = []
for order, (net, ((x1,y1),(x2,y2))) in enumerate(guide_points.items()):
    mid = (x1+x2)//2 + ((order % 13)-6)*grid
    mid = max(grid, min(width*2000-grid, mid))
    segments = [
        box(x1,y1,mid,y1,"metal11"), box(mid,y1,mid,y2,"metal12"), box(mid,y2,x2,y2,"metal11"),
        box(x1,y1,x1,y1,"metal12",0), box(x2,y2,x2,y2,"metal12",0),
        box(x1,y1,x1,y1,"metal10",0)
    ]
    if not net.endswith("_ready"):
        segments.append(box(x2,y2,x2,y2,"metal10",0))
    guides.extend([net, "(", *segments, ")"])
(out/"manual.guide").write_text("\n".join(guides)+"\n")
(out/"route.tcl").write_text("\n".join([
    "read_lef ../overlay/research12.tech.lef",
    *(f"read_lef ../{kind}.lef" for kind in "PUCFJ"),
    "read_def coupon.def", "source /OpenROAD-flow-scripts/flow/platforms/nangate45/make_tracks.tcl",
    "source ../overlay/new_tracks.tcl", "set_thread_count " + os.environ.get("SLURM_CPUS_PER_TASK", "10"), "set_routing_layers -signal metal11-metal12",
    "set_macro_extension 0", "write_db unrouted.odb",
    "pin_access -via_in_pin_bottom_layer metal10 -via_in_pin_top_layer metal10",
    "read_guides manual.guide",
    "detailed_route -droute_end_iter 12 -output_drc drc.rpt -output_guide_coverage coverage.csv -via_in_pin_bottom_layer metal10 -via_in_pin_top_layer metal10",
    "write_db routed.odb", "write_def routed.def", ""
]))
