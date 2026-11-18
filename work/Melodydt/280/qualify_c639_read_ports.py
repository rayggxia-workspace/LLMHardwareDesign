"""Bind six C639 wave windows to shared DMA and phase wrapper port declarations."""
from hashlib import sha256
import json
from pathlib import Path
import re
import sys


def read_ports(path, top):
    text = path.read_text()
    match = re.search(r"(?m)^module \\" + re.escape(top) + r"$\n(.*?)^end$", text, re.S)
    if match is None:
        raise ValueError(f"missing canonicalized module: {top}")
    ports = {}
    for line in match[1].splitlines():
        fields = line.split()
        if fields[:1] != ["wire"] or not any(d in fields for d in ("input", "output")):
            continue
        ports[fields[-1].lstrip("\\")] = int(fields[fields.index("width") + 1]) if "width" in fields else 1
    if not ports:
        raise ValueError(f"no ports found: {top}")
    return ports


def source_port(top, name):
    root = "TOP/test_native_decode638_product_replay/typed_dma"
    if top == "mc_dma_fabric_typed_p":
        return root + "/dma", name
    if name in {"clk", "reset", "owner"}:
        return root, name
    phase, _, signal = name.partition("_")
    if phase not in {"phase0", "phase1"} or not signal:
        raise ValueError(f"unknown phase-wrapper port: {name}")
    return f"{root}/{phase}", signal


audit, shared, phase, output = map(Path, sys.argv[1:])
tops = {"mc_dma_fabric_typed_p": shared, "c639_dma_phase_ports": phase}
result = {}
for top, path in tops.items():
    ports = read_ports(path, top)
    binding = result[top] = {
        "rtlil_sha256": sha256(path.read_bytes()).hexdigest(),
        "ports": len(ports), "bits": sum(ports.values()),
        "windows": {},
    }
    for index in range(2):
        for stage in ("gate-up", "down", "writer-active"):
            name = f"mode-{index}-{stage}"
            table = (audit / name / "signal-table.tsv").read_bytes()
            traced = {}
            for line in table.decode().splitlines():
                fields = line.split("\t")
                if fields[0] == "var":
                    traced[fields[1], fields[2].split()[0]] = (int(fields[3]), int(fields[4]))
            selected = {}
            for port, width in ports.items():
                scope, signal = source_port(top, port)
                actual, handle = traced.get((scope, signal), (None, None))
                if actual != width:
                    raise ValueError(f"{name}: {top}.{port} expects {width}, FST contains {actual}")
                selected[port] = {"scope": scope, "signal": signal, "width": width, "fst_handle": handle}
            binding["windows"][name] = {
                "table_sha256": sha256(table).hexdigest(),
                "ports": selected,
            }
with output.open("x") as stream:
    json.dump(result, stream, indent=2)
    stream.write("\n")
