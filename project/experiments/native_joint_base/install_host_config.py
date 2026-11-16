"""Install audited configuration wiring into the linked placement seed."""
import argparse
import collections
import gzip
import hashlib
import json
import re
import shutil
from pathlib import Path

DECLARATION = re.compile(r"  (input|output)(?: (\[\d+:\d+\]))? (\w+),?\n")
ALIAS = re.compile(r"(\w+)(?:\[(\d+)\])?")
SWITCH_WIDTHS = {
    "target_req_payload": ("driver", 322),
    "target_req_valid": ("driver", 10),
    "target_req_ready": ("sink", 10),
    "target_rsp_payload": ("sink", 1760),
    "target_rsp_valid": ("sink", 10),
    "target_rsp_ready": ("driver", 10),
}
HOST_PORTS = {
    "allow_request": ("input", 1),
    "host_req_valid": ("input", 1),
    "host_req_ready": ("output", 1),
    "host_req_target": ("input", 4),
    "host_req_payload": ("input", 322),
    "host_rsp_valid": ("output", 1),
    "host_rsp_ready": ("input", 1),
    "host_rsp_target": ("output", 4),
    "host_rsp_payload": ("output", 176),
    "host_rsp_bad_target": ("output", 1),
    "idle": ("output", 1),
}


def check(condition, message):
    if not condition:
        raise ValueError(message)


def signal(alias, widths, role):
    match = ALIAS.fullmatch(alias)
    check(match is not None, f"Invalid signal {alias}")
    stem, index = match.groups()
    check(stem in widths, f"Signal {stem} missing")
    direction, width = widths[stem]
    check(role == direction, f"Wrong signal direction: {alias}")
    check((index is None and width is None) or
          (index is not None and width is not None and int(index) <= int(width[1:-3])),
          f"Signal outside port width: {alias}")
    return stem, int(index) if index is not None else None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("join_plan", type=Path)
    parser.add_argument("mapped_switch", type=Path)
    parser.add_argument("rtl", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    with gzip.open(args.join_plan, "rt", encoding="utf-8") as stream:
        plan = json.load(stream)
    check(plan["schema"] == "issue185-host-config-logical-install-plan/1", "Unsupported plan")
    with args.input.open(encoding="utf-8") as source:
        top = source.readline()
        check(top == "module joint_base_control_placement (\n", "Unsupported placement seed")
        ports = {}
        for line in source:
            if line == ");\n":
                break
            match = DECLARATION.fullmatch(line)
            check(match is not None, f"Unsupported port declaration: {line}")
            direction, width, name = match.groups()
            check(name not in ports, f"Duplicate top port {name}")
            ports[name] = (direction, width)
        bits_used = collections.defaultdict(set)
        switch_used = set()
        assignments = []
        for group in plan["groups"]:
            switch_role = group["switch_role"]
            switch_port, bit = group["switch_pin"].rstrip("]").split("[")
            check(switch_port in SWITCH_WIDTHS, f"Unknown switch port {switch_port}")
            expected_role, width = SWITCH_WIDTHS[switch_port]
            index = int(bit)
            check(switch_role == expected_role and 0 <= index < width, f"Wrong role/width: {group['switch_pin']}")
            switch_bit = (switch_port, index)
            check(switch_bit not in switch_used, f"Duplicate switch bit {switch_bit}")
            switch_used.add(switch_bit)
            wire = f"joint_host_{switch_port}[{index}]"
            if switch_role == "sink":
                check(len(group["native_legs"]) == 1, f"Multiple native response sources {wire}")
            else:
                check(group["native_legs"], f"No target sinks {wire}")
            for leg in group["native_legs"]:
                alias = leg["prior_alias"]
                expected_leg = "sink" if switch_role == "driver" else "driver"
                expected_direction = "input" if switch_role == "driver" else "output"
                check(leg["native_role"] == expected_leg, f"Wrong native role: {alias}")
                stem, index = signal(alias, ports, expected_direction)
                check(index not in bits_used[stem], f"Duplicate native signal: {alias}")
                bits_used[stem].add(index)
                lhs, rhs = (alias, wire) if switch_role == "driver" else (wire, alias)
                assignments.append(f"  assign {lhs} = {rhs};\n")
        for padding in plan["padding"]:
            lo, hi = padding["switch_response_zero_bits"]
            for index in range(lo, hi + 1):
                bit = "target_rsp_payload", index
                check(bit not in switch_used and 0 <= index < SWITCH_WIDTHS[bit[0]][1], f"Invalid padding: {bit}")
                switch_used.add(bit)
                assignments.append(f"  assign joint_host_target_rsp_payload[{index}] = 1'b0;\n")
        expected_bits = {(port, bit) for port, (_, width) in SWITCH_WIDTHS.items() for bit in range(width)}
        check(expected_bits == switch_used, "Unbound mapped switch bit")
        for port, indices in bits_used.items():
            width = ports[port][1]
            expected = {None} if width is None else set(range(int(width[1:-3]) + 1))
            check(indices == expected, f"Only partially connected original port {port}")
        declarations = [(direction, width, name) for name, (direction, width) in ports.items()
                        if name not in bits_used]
        declarations += [(direction, f"[{width - 1}:0]" if width > 1 else None, f"joint_cfg_{name}")
                         for name, (direction, width) in HOST_PORTS.items()]
        with args.output.open("w", encoding="utf-8", newline="\n") as output:
            output.write(top)
            output.write(",\n".join(f"  {direction} {width + ' ' if width else ''}{name}"
                                    for direction, width, name in declarations))
            output.write("\n);\n")
            for name in sorted(bits_used):
                width = ports[name][1]
                output.write(f"  wire {width + ' ' if width else ''}{name};\n")
            for name, (_, width) in SWITCH_WIDTHS.items():
                output.write(f"  wire [{width - 1}:0] joint_host_{name};\n")
            output.write("  wire joint_cfg_reset;\n  INV_X1 host_reset_inverter (.A(rst_n), .ZN(joint_cfg_reset));\n")
            output.writelines(assignments)
            connections = [".clk(clk)", ".reset(joint_cfg_reset)"]
            connections += [f".{name}(joint_cfg_{name})" for name in HOST_PORTS]
            connections += [f".{name}(joint_host_{name})" for name in SWITCH_WIDTHS]
            output.write("  native_host_program_switch host_program (\n    " +
                         ",\n    ".join(connections) + "\n  );\n")
            shutil.copyfileobj(source, output)
            output.write("\n")
            with args.mapped_switch.open(encoding="utf-8") as mapped:
                shutil.copyfileobj(mapped, output)
    digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    print(json.dumps({
        "source_sha256": digest(args.input),
        "join_plan_sha256": digest(args.join_plan),
        "mapped_switch_sha256": digest(args.mapped_switch),
        "rtl_sha256": digest(args.rtl),
        "joint_seed_sha256": digest(args.output),
        "native_endpoint_bits": sum(len(indices) for indices in bits_used.values()),
        "switch_bits": len(switch_used),
        "new_host_top_ports": len(HOST_PORTS),
    }, indent=2))


if __name__ == "__main__":
    main()
