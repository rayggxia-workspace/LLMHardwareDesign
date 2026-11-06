#!/usr/bin/env python3
"""Tie a qualified pair of actual routed pins using the research upper RC model."""
import json
from pathlib import Path
import re
import shlex
import sys

from physical import run

root = Path(sys.argv[1]).resolve()
out = Path(sys.argv[2]).resolve()
out.mkdir()
physical = next((root / "flow/results/nangate45").glob("*/base/6_final.v"))
rtl = physical.read_text()
module = re.search(r"^module (\w+)", rtl, re.M)[1]
routes = json.loads((root / "overlay.json").read_text())["routes"]
native = {endpoint: f"upper_{i}" for i, route in enumerate(routes.values())
          for endpoint in (route["driver"], route["sink"])}
external = {}
connections = []
for direction, span, port in re.findall(r"^\s*(input|output|inout)\s+(\[\d+:\d+\])?\s*(\w+)\s*;", rtl, re.M):
    indices = [None]
    if span:
        high, low = map(int, span[1:-1].split(":"))
        indices = list(range(high, low - 1, -1))
    targets = []
    for bit in indices:
        name = port if bit is None else f"{port}[{bit}]"
        if name in native:
            targets.append(native.pop(name))
        else:
            name = port if bit is None else f"{port}_{bit}"
            external[name] = direction
            targets.append(name)
    value = targets[0] if not span else "{" + ", ".join(targets) + "}"
    connections.append(f"    .{port}({value})")
if native or not connections or "clk" not in external:
    raise ValueError(f"native routed-netlist bindings missing: {native}")
wrapper = out / "top.v"
wrapper.write_text(
    "module pu_overlay_timing(\n" + ",\n".join(external) + ");\n"
    + "".join(f"    {direction} {port};\n" for port, direction in external.items())
    + "".join(f"    wire upper_{i};\n" for i in range(len(routes)))
    + f"    {module} base (\n" + ",\n".join(connections) + ");\nendmodule\n"
)
platform = Path("/OpenROAD-flow-scripts/flow/platforms/nangate45")
lefs = shlex.split(re.search(r"^export ADDITIONAL_LEFS = (.+)$", (root / "config.mk").read_text(), re.M)[1])
native_spef = physical.with_suffix(".spef").read_text()
header, *bodies = re.split(r"(?m)^\*D_NET ", native_spef)
names = {name: token for token, name in re.findall(r"(?m)^(\*\d+) (\S+)$", header)}
sections = dict((body.split(maxsplit=1)[0], body) for body in bodies)
endpoint_nodes = {}
sink_aliases = {}
pairs = []
for i, route in enumerate(routes.values()):
    send, receive = route["driver"], route["sink"]
    if send not in names or receive not in names:
        raise ValueError(f"Missing native parasitics for {send} -> {receive}")
    source, sink = names[send], names[receive]
    if source not in sections or sink not in sections:
        raise ValueError(f"Missing native routed net for {send} -> {receive}")
    sink_aliases[sink] = source
    endpoint_nodes[send] = f"{source}:1000000"
    endpoint_nodes[receive] = f"{source}:1000001"
    pairs.append((source, sink, endpoint_nodes[send], endpoint_nodes[receive], route["length_um"]))
alternation = "|".join(map(re.escape, endpoint_nodes))
sink_node = re.compile(r"(?<!\S)(" + "|".join(map(re.escape, sink_aliases)) + r"):(\d+)(?=\s|$)")
ports = re.compile(rf"(?m)^(?:\*P )?(?:{alternation}) [IOB]\n")
node_token = re.compile(rf"(?<!\S)(?:{alternation})(?=\s|$)")


def fields(body):
    first, connections = body.split("\n*CONN\n")
    pins, rest = connections.split("\n*CAP\n")
    caps, resistors = rest.split("\n*RES\n")
    resistors, _ = resistors.split("\n*END", 1)
    return float(first.split()[1]), pins.splitlines(), caps.splitlines(), resistors.splitlines()


def renumber(lines):
    return "".join(f"{i} {line.split(maxsplit=1)[1]}\n" for i, line in enumerate(lines, 1))


def replace_endpoints(text):
    rewritten = node_token.sub(lambda m: endpoint_nodes[m.group()], ports.sub("", text))
    return sink_node.sub(lambda m: f"{sink_aliases[m[1]]}:{2000000+int(m[2])}", rewritten)


header = ports.sub("", header)
sections = {name: replace_endpoints(body) for name, body in sections.items()}
reset_constraints = []
if "rst_ni" in external:
    reset_constraints = [
        "set raw_reset [get_ports rst_ni]",
        "set reset_sinks [get_fanout -flat -endpoints_only -from $raw_reset]",
        'if {[llength $reset_sinks] != 2} {error "raw reset must reach exactly two synchronizer pins"}',
        'foreach sink $reset_sinks {if {![string match */RN [get_full_name $sink]]} {error "unexpected raw reset endpoint"}}',
        "set_false_path -from $raw_reset -to $reset_sinks",
    ]
tech = json.loads((Path(__file__).parents[1] / "block_v1/technology-2um-v1.json").read_text())
electrical = tech["electrical"]
geometry = tech["geometry_um"]
variants = {}
for variant, scale in electrical["estimate_variants"].items():
    joined = dict(sections)
    for source, sink, near, far, length in pairs:
        a, ac, ap, ar = fields(joined[source])
        b, bc, bp, br = fields(joined.pop(sink))
        cap_pf = scale * .155390385 * length / 1000
        resistance = scale * (electrical["sheet_resistance_ohm"] * length / geometry["width"]
                              + 4 * electrical["via_resistance_ohm"])
        cap = ap + bp + [f"0 {near} {cap_pf/2:.9f}", f"0 {far} {cap_pf/2:.9f}"]
        res = ar + br + [f"0 {near} {far} {resistance:.9f}"]
        joined[source] = (f"{source} {a+b+cap_pf:.9f}\n*CONN\n" + "\n".join(ac+bc) +
                          "\n*CAP\n" + renumber(cap) + "*RES\n" + renumber(res) + "*END\n\n")
    parasitics = out / f"{variant}.spef"
    parasitics.write_text(header + "".join("*D_NET " + body for body in joined.values()))
    tcl = out / f"{variant}.tcl"
    tcl.write_text("\n".join([
        f"read_lef {{{platform/'lef/NangateOpenCellLibrary.tech.lef'}}}",
        f"read_lef {{{platform/'lef/NangateOpenCellLibrary.macro.mod.lef'}}}",
        *(f"read_lef {{{lef}}}" for lef in lefs),
        f"read_liberty {{{platform/'lib/NangateOpenCellLibrary_typical.lib'}}}",
        *(f"read_liberty {{{lib}}}" for lib in sorted(root.glob("*.lib"))),
        f"read_verilog {{{physical}}}",
        f"read_verilog {{{wrapper}}}",
        "link_design -hier pu_overlay_timing",
        "create_clock -name clk -period 3.333333333333 [get_ports clk]",
        "set_clock_uncertainty 0.1 [get_clocks clk]",
        "set data_in [get_ports {" + " ".join(p for p, d in external.items() if p != "clk" and d == "input") + "}]",
        "set_input_delay -clock clk -max 0.8 $data_in",
        "set_input_delay -clock clk -min 0.2 $data_in",
        "set_output_delay -clock clk -max 0.8 [all_outputs]",
        "set_output_delay -clock clk -min 0.2 [all_outputs]",
        "set_load 50 [all_outputs]",
        *reset_constraints,
        f"read_spef -path base {{{parasitics}}}",
        "set_propagated_clock [all_clocks]",
        "report_worst_slack -max -digits 6",
        "report_worst_slack -min -digits 6",
        'puts "=== UPPER ROUTES ==="',
        f"if {{[llength [get_nets {{upper_*}}]] != {len(routes)}}} {{error \"Missing upper nets\"}}",
        'foreach net [get_nets {upper_*}] {report_net [get_full_name $net]}',
        'puts "=== ELECTRICAL VIOLATIONS ==="',
        "report_check_types -violators -max_capacitance -max_slew -max_fanout -digits 6",
        "report_parasitic_annotation",
        'puts "=== UPPER TIMING PATHS ==="',
        "set upper_pins [get_pins -of_objects [get_nets {upper_*}]]",
        "report_checks -through $upper_pins -path_delay min_max -group_path_count 10 -digits 6",
    ]) + "\n")
    log = out / f"{variant}.log"
    run(["openroad", "-no_init", "-exit", str(tcl)], log)
    text = log.read_text()
    slacks = {kind: float(value) for kind, value in
              re.findall(r"worst slack (max|min) (-?\d+\.\d+)", text)}
    upper_paths = text.split("=== UPPER TIMING PATHS ===", 1)[1]
    upper_nets, electrical_report = text.split("=== UPPER ROUTES ===", 1)[1].split(
        "=== ELECTRICAL VIOLATIONS ===", 1)
    wire_caps = re.findall(r"Wire capacitance:\s*([\d.]+)", upper_nets)
    variants[variant] = {
        "slack_ns": slacks,
        "annotated_upper_nets": sum(float(cap) > 0 for cap in wire_caps),
        "timed_upper_paths": upper_paths.count("Startpoint:"),
        "electrical_pass": "(VIOLATED)" not in electrical_report,
    }
(out / "upper-timing.json").write_text(json.dumps(variants, indent=2) + "\n")
if any(v["slack_ns"].keys() != {"min", "max"} or min(v["slack_ns"].values()) < 0
       or v["annotated_upper_nets"] != len(routes) or not v["timed_upper_paths"]
       or not v["electrical_pass"] for v in variants.values()):
    raise RuntimeError(f"upper timing or electrical checks failed: {variants}")
