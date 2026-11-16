"""Extract the routed M boundary ports from a frozen C639 RTL FST converted to VCD."""
import json
from pathlib import Path
import re
import sys


def extract(netlist, raw, output, target, first, last):
    port_pattern = r"^\s*(input|output)\s+(?:\[(\d+):(\d+)\]\s+)?(\w+);"
    ports = {}
    for line in netlist.open():
        if match := re.match(port_pattern, line):
            direction, high, low, name = match.groups()
            ports[name] = (direction, int(high) - int(low) + 1 if high else 1)
        elif re.match(r"^\s*wire ", line):
            break
    if sum(width for _, width in ports.values()) != 1330:
        raise ValueError("unexpected routed M interface size")

    selected = {}
    paths = []
    with raw.open() as src, output.open("w") as dst:
        dst.write("$timescale 1ps $end\n$scope module dut $end\n")
        for line in src:
            fields = line.split()
            if not fields:
                continue
            command = fields[0]
            if command == "$scope":
                paths.append(fields[2])
            elif command == "$upscope":
                paths.pop()
            elif command == "$var" and "/".join(paths) == target and fields[4] in ports:
                name = fields[4]
                width = int(fields[2])
                if name in selected or width != ports[name][1]:
                    raise ValueError(f"mismatched or duplicate port: {name}")
                selected[name] = fields[3]
                fields[1] = "wire"
                dst.write(" ".join(fields) + "\n")
            elif command == "$enddefinitions":
                break
        if set(selected) != set(ports):
            raise ValueError(f"missing ports: {set(ports) - set(selected)}")
        dst.write("$upscope $end\n$enddefinitions $end\n")
        identifiers = set(selected.values())
        time = None
        known = {}
        clock = []
        for line in src:
            if line.startswith("#"):
                time = int(line[1:])
                dst.write(f"#{time - first}\n")
                continue
            fields = line.split()
            if not fields:
                continue
            token = fields[0]
            if token[0] in "01xz":
                value, ident = token[0], token[1:]
            elif token[0] in "bB" and len(fields) == 2:
                value, ident = token[1:].lower(), fields[1]
            else:
                continue
            if ident in identifiers:
                if time is None or set(value) - {"0", "1"}:
                    raise ValueError(f"invalid value for {ident} at {time}: {value}")
                if ident == selected["clk"] and value != known.get(ident):
                    clock.append(time)
                known[ident] = value
                dst.write(line)
        if time != last or clock != list(range(first, last + 1, 5000)) or set(known) != identifiers:
            raise ValueError(f"unexpected clock, timestamp or coverage: {time=} {len(clock)=}")
    receipt = {"rtl_scope": target, "window_ps": last - first, "clock_period_ps": 10000,
               "port_bits": {direction: sum(width for kind, width in ports.values() if kind == direction)
                             for direction in ("input", "output")}}
    output.with_suffix(".json").write_text(json.dumps(receipt, indent=2) + "\n")


if __name__ == "__main__":
    netlist, raw, output, target, first, last = sys.argv[1:]
    extract(Path(netlist), Path(raw), Path(output), target, int(first), int(last))
