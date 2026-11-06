"""Generate a physical coupon for the FFN split data path on real P16 pins.

The direct 128-bit payload is a subset of the eventual cross-block service.
Control, PG, and clock sidecars are outside the coupon.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re

from compile_slice import P16_ABI


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mapping", type=Path)
    parser.add_argument("lef", type=Path)
    parser.add_argument("tech", type=Path)
    parser.add_argument("tracks", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--gap", type=int, choices=(128, 256), default=128)
    args = parser.parse_args()
    out = args.output
    out.mkdir()
    lef_bytes = args.lef.read_bytes()
    lef = lef_bytes.decode()
    master = re.search(r"^MACRO\s+(\S+)", lef, re.M)[1]
    size = tuple(map(float, re.search(r"^\s+SIZE\s+([\d.]+) BY ([\d.]+)", lef, re.M).groups()))
    if size != (3100, 3100):
        raise ValueError("expected accepted P16 size")
    pin_shapes = {}
    for match in re.finditer(r"^\s+PIN (\S+)\s*\n(.*?)^\s+END \1\s*$", lef, re.M | re.S):
        rect = re.search(r"LAYER metal10\s*;\s*RECT\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)", match[2])
        if rect:
            x0, y0, x1, y1 = map(float, rect.groups())
            pin_shapes[match[1]] = (round((x0 + x1) * 1000), round((y0 + y1) * 1000))
    gap = args.gap
    x1 = (2 * gap + 3100 + 7) // 8 * 8
    nets = []
    centers = []
    artifact_bytes = args.mapping.read_bytes()
    artifact = json.loads(artifact_bytes)
    if artifact["abi"] != P16_ABI or artifact["base_id"] != f"p16-pair-payload-g{gap}-v0":
        raise ValueError("mapping uses a different physical base or ABI")
    bundle, = artifact["bundles"]
    for wire in bundle["wires"]:
        if wire["kind"] != "payload":
            continue
        a, a_pin = wire["driver"].split(".", 1)
        b, b_pin = wire["sink"].split(".", 1)
        if (a, b) != ("P1", "P0") or not {a_pin, b_pin} <= pin_shapes.keys():
            raise ValueError(f"missing exact P16 pin: {wire}")
        nets.append(f"- {wire['name']} ( {a} {a_pin} ) ( {b} {b_pin} ) + USE SIGNAL ;")
        sx, sy = pin_shapes[a_pin]
        dx, dy = pin_shapes[b_pin]
        centers.append((wire["name"], sx + x1 * 2000, sy + gap * 2000,
                        dx + gap * 2000, dy + gap * 2000))
    if len(nets) != 128:
        raise ValueError("payload must have 128 bits")
    (out / "coupon.def").write_text("\n".join([
        "VERSION 5.8 ;", 'DIVIDERCHAR "/" ;', 'BUSBITCHARS "[]" ;',
        "DESIGN p16_ffn_payload ;", "UNITS DISTANCE MICRONS 2000 ;",
        f"DIEAREA ( 0 0 ) ( {(x1+3100+gap)*2000} {(3100+2*gap)*2000} ) ;",
        "COMPONENTS 2 ;", f"- P0 {master} + FIXED ( {gap*2000} {gap*2000} ) N ;",
        f"- P1 {master} + FIXED ( {x1*2000} {gap*2000} ) N ;", "END COMPONENTS",
        f"NETS {len(nets)} ;", *nets, "END NETS", "END DESIGN", "",
    ]), encoding="ascii")
    def guide_box(x0, y0, x1, y1, layer):
        grid = 120000
        lo_x, hi_x = sorted((x0 // grid, x1 // grid))
        lo_y, hi_y = sorted((y0 // grid, y1 // grid))
        return f"{max(0, lo_x-1)*grid} {max(0, lo_y-1)*grid} {(hi_x+2)*grid} {(hi_y+2)*grid} {layer}"

    guides = []
    for i, (name, x0, y0, x1, y1) in enumerate(centers):
        mid = (x0 + x1) // 2 + (i % 9 - 4) * 120000
        guides.extend([name, "(",
                       guide_box(x0, y0, mid, y0, "metal11"),
                       guide_box(mid, y0, mid, y1, "metal12"),
                       guide_box(mid, y1, x1, y1, "metal11"),
                       ")"])
    (out / "payload.guide").write_text("\n".join(guides) + "\n", encoding="ascii")
    threads = int(os.environ.get("SLURM_CPUS_PER_TASK", "1"))
    (out / "route.tcl").write_text("\n".join([
        f"read_lef {{{args.tech.resolve()}}}", f"read_lef {{{args.lef.resolve()}}}",
        "read_def coupon.def", "source /OpenROAD-flow-scripts/flow/platforms/nangate45/make_tracks.tcl",
        f"source {{{args.tracks.resolve()}}}", f"set_thread_count {threads}",
        "set_routing_layers -signal metal11-metal12",
        "set_macro_extension 0",
        "pin_access -via_access_layer metal10 -via_in_pin_bottom_layer metal10 -via_in_pin_top_layer metal10",
        'if {[catch {global_route -guide_file route.guide} message]} {',
        '  puts "GRT_FALLBACK $message"; read_guides payload.guide',
        '}',
        "detailed_route -via_access_layer metal10 -droute_end_iter 12 -output_drc drc.rpt -via_in_pin_bottom_layer metal10 -via_in_pin_top_layer metal10",
        "write_def routed.def", "",
    ]), encoding="ascii")
    receipt = {"base_id": f"p16-pair-payload-g{gap}-v0", "block_abi": P16_ABI,
               "bundle_id": bundle["id"], "scope": "128-bit payload only",
               "p16_lef_sha256": hashlib.sha256(lef_bytes).hexdigest(),
               "mapping_sha256": hashlib.sha256(artifact_bytes).hexdigest(),
               "tech_sha256": hashlib.sha256(args.tech.read_bytes()).hexdigest(),
               "tracks_sha256": hashlib.sha256(args.tracks.read_bytes()).hexdigest(),
               "expected_nets": len(nets), "threads": threads}
    (out / "coupon.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
