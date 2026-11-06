"""Audit the Qwen candidate graph and generate passive, uniquely bound DEF subsets."""

import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path
import re


# PR #176, COMPOSITE_MODEL_FLOWS.md section 8. These are S-to-S transfers.
TRANSFERS = {
    "U0:P2": "Norm / projection input",
    "P2:U0": "Attention Q/K",
    "U0:P0": "Q / FFN input",
    "U0:P1": "FFN input",
    "P2:F0": "Attention gate / GDN z and beta",
    "P2:C0": "GDN QKV",
    "C0:U0": "GDN Q/K",
    "U0:C0": "GDN normalized Q/K return",
    "C0:U1": "GDN output",
    "U1:C0": "GDN normalized output return",
    "F0:C0": "GDN gate and beta",
    "C0:P2": "GDN gated output",
    "P0:U1": "Attention QK scores",
    "U1:P1": "Attention probabilities",
    "P1:F0": "Attention context",
    "F0:P2": "Attention gated output",
    "P1:P0": "FFN up projection",
    "P0:P2": "FFN intermediate",
    "P2:J0": "Attention / GDN output projection",
    "P2:J1": "FFN down projection",
    "J0:U0": "Layer / FFN input normalization",
    "J0:J1": "Residual Y",
    "J1:J0": "Next-layer input X",
}
PAIR = ("C0:U0", "U0:C0")
MIXED = PAIR + ("U1:P1", "P1:F0", "F0:P2")
CASES = {
    "pair": PAIR,
    "attention": PAIR + ("U1:P1",),
    "mixed": MIXED,
    "wide": MIXED + ("P0:U1", "P2:J0", "J0:J1", "J1:J0"),
    "gdn": ("C0:U1", "U1:C0", "P2:U0", "U0:P2"),
}


def read_lef(path):
    raw = path.read_bytes()
    text = raw.decode()
    master = re.search(r"^MACRO\s+(\S+)", text, re.M)[1]
    pins = {}
    for match in re.finditer(r"^\s+PIN (\S+)\s*\n(.*?)^\s+END \1\s*$", text, re.M | re.S):
        pin, body = match.groups()
        direction = re.search(r"DIRECTION\s+(\w+)\s*;", body)
        rect = re.search(
            r"LAYER metal10\s*;\s*RECT\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)",
            body,
        )
        if direction and rect:
            pins[pin] = direction[1], tuple(round(float(value) * 2000) for value in rect.groups())
    return master, pins, hashlib.sha256(raw).hexdigest()


def has_memory_port(block):
    return block[0] in "PJ"


def port(block, direction, lane, bit):
    if has_memory_port(block):
        bus = "io_rsp_data" if direction == "OUTPUT" else "io_req_data"
    else:
        bus = "tx_data" if direction == "OUTPUT" else "rx_data"
    return f"{bus}[{lane * 128 + bit}]"


def landing(lefs, positions, block, name, direction):
    pin = lefs[block[0]][1].get(name)
    if pin is None or pin[0] != direction:
        return None
    x, y = positions[block]
    rect = tuple(value + 2000 * offset for value, offset in zip(pin[1], (x, y, x, y)))
    xl, yl, xh, yh = rect
    if min(xh - xl, yh - yl) < 4000:
        return None
    if ((xl + xh) // 2 - 190) % 8000 or ((yl + yh) // 2 - 140) % 8000:
        return None
    return rect


def dump(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def audit(lefs, positions, out):
    fan_out = Counter(edge.split(":")[0] for edge in TRANSFERS)
    fan_in = Counter(edge.split(":")[1] for edge in TRANSFERS)
    blocks = {}
    for block in positions:
        capacity = 2 if has_memory_port(block) else 1
        blocks[block] = dict(
            native_port_type="SRAM request/response" if has_memory_port(block) else "S TX/RX",
            physical_tx_lanes=capacity, physical_rx_lanes=capacity,
            logical_tx_peers=fan_out[block], logical_rx_peers=fan_in[block],
            extra_tx_peers=max(0, fan_out[block] - capacity),
            extra_rx_peers=max(0, fan_in[block] - capacity),
        )
    with (out / "payload-demand.tsv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(("edge", "function", "bit", "src_candidate", "dst_candidate",
                         "src_M10_dbu", "dst_M10_dbu", "binding"))
        for edge, purpose in TRANSFERS.items():
            src, dst = edge.split(":")
            collision = blocks[src]["extra_tx_peers"] or blocks[dst]["extra_rx_peers"]
            for bit in range(128):
                tx = port(src, "OUTPUT", 0, bit)
                rx = port(dst, "INPUT", 0, bit)
                a = landing(lefs, positions, src, tx, "OUTPUT")
                b = landing(lefs, positions, dst, rx, "INPUT")
                status = "requires_endpoint_allocation" if collision else "candidate_payload_only"
                if a is None or b is None:
                    status = "unavailable_m10_landing"
                writer.writerow((edge, purpose, bit, f"{src}/{tx}", f"{dst}/{rx}",
                                 ",".join(map(str, a or ())), ",".join(map(str, b or ())), status))
    dump(out / "binding-audit.json", dict(
        mapping="PR #176 section 8, 08f2ea20a11dfdd09892a67599163e32b7237edb",
        logical_transfers=TRANSFERS, payload_bits_per_transfer=128,
        physical_ports=blocks, lef_sha256={k: value[2] for k, value in lefs.items()},
        unresolved_interfaces=[
            "multi-peer port selection and reservation",
            "transaction address, request, ready and destination write confirmation",
            "physical parent transport and MEM / KV / state interfaces",
            "clock, reset and power integration",
        ],
        complete_product_binding=False,
    ))


def write_case(lefs, base, out, case):
    positions = base["positions_um"]
    rects, endpoints = {}, {}
    claimed = set()
    unavailable = []
    source_lanes, dest_lanes = Counter(), Counter()

    def add(net, a, b):
        if a in claimed or b in claimed:
            raise ValueError(f"shared physical pin in {net}: {a}, {b}")
        ra = landing(lefs, positions, *a, "OUTPUT")
        rb = landing(lefs, positions, *b, "INPUT")
        if ra is None or rb is None:
            unavailable.append(dict(net=net, source=a, sink=b, source_rect=ra, sink_rect=rb))
            return
        rects[net] = [ra, rb]
        endpoints[net] = [a, b]
        claimed.update((a, b))

    for edge in CASES[case]:
        src, dst = edge.split(":")
        tx, rx = source_lanes[src], dest_lanes[dst]
        if tx >= (2 if has_memory_port(src) else 1) or rx >= (2 if has_memory_port(dst) else 1):
            raise ValueError(f"case has insufficient physical ports for {edge}")
        source_lanes[src] += 1
        dest_lanes[dst] += 1
        for bit in range(128):
            add(f"{src}_{dst}_data_{bit}",
                (src, port(src, "OUTPUT", tx, bit)), (dst, port(dst, "INPUT", rx, bit)))

    for bit in range(32):
        add(f"p_gate_{bit}", ("P0", f"m_to_g_data[{bit}]"), ("P0", f"g_from_m_data[{bit}]"))
    add("p_gate_valid", ("P0", "m_to_g_valid"), ("P0", "g_from_m_valid"))
    add("p_gate_take", ("P0", "g_from_m_take"), ("P0", "m_to_g_take"))

    dump(out / "case-binding.json", dict(
        case=case, logical_edges=CASES[case], requested_nets=128 * len(CASES[case]) + 34,
        bound_nets=len(endpoints), unavailable_endpoints=unavailable, endpoints=endpoints,
    ))
    if unavailable:
        raise SystemExit("Case has unavailable real M10 endpoints. See case-binding.json.")

    width, height = base["die_um"]
    components = [f"- {name} {lefs[name[0]][0]} + FIXED ( {x*2000} {y*2000} ) N ;"
                  for name, (x, y) in positions.items()]
    nets = [f"- {name} ( {a[0]} {a[1]} ) ( {b[0]} {b[1]} ) + USE SIGNAL ;"
            for name, (a, b) in endpoints.items()]
    (out / "coupon.def").write_text("\n".join([
        "VERSION 5.8 ;", 'DIVIDERCHAR "/" ;', 'BUSBITCHARS "[]" ;',
        "DESIGN qwen_payload_coupon ;", "UNITS DISTANCE MICRONS 2000 ;",
        f"DIEAREA ( 0 0 ) ( {width*2000} {height*2000} ) ;",
        f"COMPONENTS {len(components)} ;", *components, "END COMPONENTS",
        "PINS 0 ;", "END PINS", f"NETS {len(nets)} ;", *nets, "END NETS", "END DESIGN", "",
    ]), encoding="ascii")
    dump(out / "inputs.json", dict(
        base, macro_endpoint_rects_dbu=rects, includes_p=True, isolated=False,
        synthetic_ready_sinks=0, transport_implemented=False,
    ))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Input dir with five LEFs and #194 inputs.json")
    parser.add_argument("out", type=Path)
    parser.add_argument("case", choices=tuple(CASES) + ("audit",))
    args = parser.parse_args()
    base = json.loads((args.input / "inputs.json").read_text())
    lefs = {kind: read_lef(args.input / f"{kind}.lef") for kind in "PUCFJ"}
    args.out.mkdir(parents=True)
    if args.case == "audit":
        audit(lefs, base["positions_um"], args.out)
    else:
        write_case(lefs, base, args.out, args.case)


if __name__ == "__main__":
    main()
