"""Generate upper-metal signal nets from actual native macro and switch LEFs."""

import argparse
import itertools
import json
from pathlib import Path
import re

from qwen_candidate import dump, landing, read_lef


def lef_size(path):
    return tuple(round(float(x)) for x in re.search(
        r"^\s+SIZE\s+(\S+) BY (\S+)", path.read_text(), re.M).groups())


def ports(profile):
    """Yield named output/input pair; packed bit order follows the RTL wrapper."""
    switch = "T0"

    def pair(block, a, b, to_block):
        return ((switch, a), (block, b)) if to_block else ((block, b), (switch, a))

    def bus(block, a, b, width, offset, to_block):
        for bit in range(width):
            yield pair(block, f"{a}[{width*offset+bit}]", f"{b}[{bit}]", to_block)

    def channel(block, index, prefix, signals):
        for name, to_block in signals:
            yield pair(block, f"{prefix}{name}[{index}]", name, to_block)

    tx = (("tx_req", True), ("tx_take", True), ("tx_ready", False), ("tx_valid", False))
    rx = (("rx_valid", True), ("rx_stored_ready", True), ("rx_ready", False), ("rx_stored", False))
    if profile == "c0":
        for index, block in enumerate(("U0", "U1", "F0")):
            yield from channel(block, index, "", tx)
            yield from bus(block, "tx_addr", "tx_addr", 10, index, True)
            yield from bus(block, "tx_data", "tx_data", 128, index, False)
        for name, to_block in rx:
            yield pair("C0", f"c0_{name}", name, to_block)
        yield from bus("C0", "c0_rx_addr", "rx_addr", 10, 0, True)
        yield from bus("C0", "c0_rx_data", "rx_data", 128, 0, True)
        for name, to_block in (("req_valid", True), ("req_write", True), ("req_ready", False),
                               ("rsp_valid", False), ("rsp_ready", True)):
            yield pair("P2", f"p2_{name}", f"io_{name}[0]", to_block)
        yield from bus("P2", "p2_req_addr", "io_req_addr", 10, 0, True)
        yield from bus("P2", "p2_rsp_data", "io_rsp_data", 128, 0, False)
    else:
        for index, block in enumerate(("U0", "U1", "C0", "F0")):
            yield from channel(block, index, "ucf_", tx + rx)
            for name, width, to_block in (("tx_addr", 10, True), ("tx_data", 128, False),
                                          ("rx_addr", 10, True), ("rx_data", 128, True)):
                yield from bus(block, f"ucf_{name}", name, width, index, to_block)
        for index, block in enumerate(("P0", "P1", "P2", "J0", "J1")):
            for name, to_block in (("req_valid", True), ("req_write", True), ("req_ready", False),
                                   ("rsp_valid", False), ("rsp_ready", True)):
                yield pair(block, f"pj_{name}[{index}]", f"io_{name}[0]", to_block)
            for name, width, to_block in (("req_addr", 10, True), ("req_data", 128, True),
                                          ("rsp_data", 128, False)):
                yield from bus(block, f"pj_{name}", f"io_{name}", width, index, to_block)


def place(base, switch_size, mode):
    positions = {k: tuple(v) for k, v in base["positions_um"].items()}
    sizes = dict(base["sizes_um"], T=switch_size)
    width, height = base["die_um"]
    if mode == "east":
        positions["T0"] = ((width + 255)//8*8, (height//2-switch_size[1]//2)//8*8)
    elif mode == "north":
        positions["T0"] = (positions["C0"][0], (height + 255)//8*8)
    else:
        cut = positions["C0"][1]
        positions = {name: (x, y+switch_size[1]+512 if y >= cut else y)
                     for name, (x, y) in positions.items()}
        positions["T0"] = ((width//2-switch_size[0]//2)//8*8, cut+128)
    boxes = {}
    for name, (x, y) in positions.items():
        w, h = sizes[name[0]]
        boxes[name] = x, y, x+w, y+h
    for (a, (x1,y1,x2,y2)), (b, (u1,v1,u2,v2)) in itertools.combinations(boxes.items(), 2):
        if min(x2,u2) > max(x1,u1) and min(y2,v2) > max(y1,v1):
            raise ValueError(f"overlapping macro footprints {a} {b}")
    return positions, sizes, (max(b[2] for b in boxes.values())+256,
                              max(b[3] for b in boxes.values())+256)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", type=Path)
    parser.add_argument("switch", type=Path, help="LEF from a native routed switch")
    parser.add_argument("switch_gds", type=Path)
    parser.add_argument("out", type=Path)
    parser.add_argument("profile", choices=("c0", "nine"))
    parser.add_argument("placement", choices=("east", "north", "channel"))
    args = parser.parse_args()
    base = json.loads((args.inputs/"inputs.json").read_text())
    sizes_switch = lef_size(args.switch)
    positions, sizes, die = place(base, sizes_switch, args.placement)
    lefs = {kind: read_lef(args.inputs/f"{kind}.lef") for kind in "PUCFJ"}
    lefs["T"] = read_lef(args.switch)
    args.out.mkdir(parents=True)
    endpoints, rects, missing = {}, {}, []
    used = set()
    desired = list(ports(args.profile))
    for i, (source, sink) in enumerate(desired):
        if source in used or sink in used:
            raise ValueError(f"duplicate native terminal: {source}, {sink}")
        used.update((source,sink))
        a = landing(lefs, positions, *source, "OUTPUT")
        b = landing(lefs, positions, *sink, "INPUT")
        if a is None or b is None:
            missing.append(dict(source=source, sink=sink, source_m10=a, sink_m10=b))
            continue
        name = f"word_{i:04d}"
        endpoints[name] = [source,sink]
        rects[name] = [a,b]
    dump(args.out/"case-binding.json", dict(
        profile=args.profile, placement=args.placement, requested_nets=len(desired),
        bound_nets=len(endpoints), missing=missing, endpoints=endpoints,
        unbound_switch_signal_terminals=sorted(set(lefs["T"][1])-{pin for block,pin in used if block=="T0"}),
        lefs_sha256={k: v[2] for k,v in lefs.items()},
    ))
    if missing:
        raise SystemExit(f"{len(missing)} physical signal landings unavailable")
    parts = [f"- {name} {lefs[name[0]][0]} + FIXED ( {x*2000} {y*2000} ) N ;"
             for name,(x,y) in positions.items()]
    nets = [f"- {net} ( {a[0]} {a[1]} ) ( {b[0]} {b[1]} ) + USE SIGNAL ;"
            for net,(a,b) in endpoints.items()]
    (args.out/"coupon.def").write_text("\n".join([
        "VERSION 5.8 ;", 'DIVIDERCHAR "/" ;', 'BUSBITCHARS "[]" ;',
        "DESIGN qwen_switch_upper ;", "UNITS DISTANCE MICRONS 2000 ;",
        f"DIEAREA ( 0 0 ) ( {die[0]*2000} {die[1]*2000} ) ;",
        f"COMPONENTS {len(parts)} ;", *parts, "END COMPONENTS", "PINS 0 ;", "END PINS",
        f"NETS {len(nets)} ;", *nets, "END NETS", "END DESIGN", "",
    ]))
    dump(args.out/"inputs.json", dict(positions_um=positions, sizes_um=sizes, die_um=die,
                                    macro_endpoint_rects_dbu=rects, synthetic_ready_sinks=0))
    native = json.loads((args.inputs/"native-gds.json").read_text())
    native["T"] = str(args.switch_gds.resolve(strict=True))
    dump(args.out/"gds-inputs.json", {name: native[name[0]] for name,_ in sorted(used)})


if __name__ == "__main__":
    main()
