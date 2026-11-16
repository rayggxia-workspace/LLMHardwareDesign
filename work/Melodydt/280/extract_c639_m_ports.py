"""Extract the routed M boundary ports from a frozen C639 RTL FST converted to VCD."""
import json
from pathlib import Path
import re
import sys


def extract(netlist, raw, output, target, first, last, frequency, expected_port_bits=1330, untraced_ports=()):
    port_pattern = r"^\s*(input|output)\s+(?:\[(\d+):(\d+)\]\s+)?(\w+);"
    ports = {}
    for line in netlist.open():
        if match := re.match(port_pattern, line):
            direction, high, low, name = match.groups()
            ports[name] = (direction, int(high) - int(low) + 1 if high else 1)
        elif re.match(r"^\s*wire ", line):
            break
    routed_bits = sum(width for _, width in ports.values())
    if not ports or (expected_port_bits is not None and routed_bits != expected_port_bits):
        raise ValueError(f"unexpected routed interface size: {routed_bits}, expected {expected_port_bits} bits")
    for name in untraced_ports:
        if name not in ports or ports[name][0] != "output":
            raise ValueError(f"untraced port must be a routed output: {name}")

    if frequency not in (100, 300):
        raise ValueError("expected 100 or 300 MHz")
    source_clock_mhz = 100

    def retime(time):
        return ((time - first) * source_clock_mhz + frequency // 2) // frequency

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
        missing = set(ports) - set(selected)
        if missing - set(untraced_ports):
            raise ValueError(f"missing required ports: {missing - set(untraced_ports)}")
        dst.write("$upscope $end\n$enddefinitions $end\n")
        identifiers = set(selected.values())
        time = None
        known = {}
        clock = []
        for line in src:
            if line.startswith("#"):
                time = int(line[1:])
                dst.write(f"#{retime(time)}\n")
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
    receipt = {"rtl_scope": target, "window_ps": retime(last), "clock_hz": frequency * 1000000,
               "source_period_ps": 10000, "timestamp_resolution_ps": 1,
               "routed_port_bits": routed_bits,
               "untraced_port_bits": {name: ports[name][1] for name in sorted(missing)},
               "port_bits": {direction: sum(ports[name][1] for name in selected if ports[name][0] == direction)
                             for direction in ("input", "output")}}
    output.with_suffix(".json").write_text(json.dumps(receipt, indent=2) + "\n")


if __name__ == "__main__":
    netlist, raw, output, target, first, last, frequency = sys.argv[1:]
    extract(Path(netlist), Path(raw), Path(output), target, int(first), int(last), int(frequency))
