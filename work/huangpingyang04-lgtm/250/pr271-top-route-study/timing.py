"""Emit and summarize Liberty/OpenSTA timing for paired one-sink toy routes."""

import argparse
import json
from pathlib import Path
import re

from resource_search import length


RC_C_FF_PER_UM = .155390385 * 1.5
RC_R_OHM_PER_UM = .015 * 1.5
VIA_C_FF = .2
VIA_R_OHM = .08 * 1.5


def read(path):
    return json.loads(path.read_text())


def spef(name, src, sink, route):
    um = length(route) / 2000
    vias = len(route["via10"]) + len(route["via11"])
    cap = (um * RC_C_FF_PER_UM + vias * VIA_C_FF) / 1000
    res = um * RC_R_OHM_PER_UM + vias * VIA_R_OHM
    nodes = [src, *(f"{name}:{i}" for i in range(1, 4)), sink]
    return "\n".join([
        f"*D_NET {name} {cap:.9f}", "*CONN", f"*I {src} O", f"*I {sink} I", "*CAP",
        *(f"{i} {node} {cap*weight:.9f}" for i, (node, weight) in
          enumerate(zip(nodes, (.125, .25, .25, .25, .125)), 1)),
        "*RES", *(f"{i} {a} {b} {res/4:.9f}" for i, (a, b) in enumerate(zip(nodes, nodes[1:]), 1)),
        "*END",
    ])


def emit(directory, liberty, routes, buffered):
    directory.mkdir()
    module = ["module toy(input clk, input din, output dout);",
              "wire start, pre, post;",
              "DFF_X1 launch(.D(din),.CK(clk),.Q(start),.QN());",
              "BUF_X4 original_driver(.A(start),.Z(pre));"]
    if buffered:
        module.append("BUF_X32 relay(.A(pre),.Z(post));")
    module += [f"DFF_X1 capture(.D({'post' if buffered else 'pre'}),.CK(clk),.Q(dout),.QN());", "endmodule"]
    (directory/"toy.v").write_text("\n".join(module)+"\n")
    sections = ['*SPEF "IEEE 1481-1998"', '*DESIGN "toy"', '*DATE "2026-11-15"',
                '*VENDOR "LLMHardwareDesign"', '*PROGRAM "PR271 research RC"', '*VERSION "1"',
                '*DESIGN_FLOW "PIN_CAP NONE"', '*DIVIDER /', '*DELIMITER :', '*BUS_DELIMITER [ ]',
                '*T_UNIT 1 NS', '*C_UNIT 1 PF', '*R_UNIT 1 OHM', '*L_UNIT 1 HENRY']
    sections.append(spef("pre", "original_driver:Z", "relay:A" if buffered else "capture:D", routes[0]))
    if buffered:
        sections.append(spef("post", "relay:Z", "capture:D", routes[1]))
    (directory/"toy.spef").write_text("\n".join(sections)+"\n")
    (directory/"run.tcl").write_text("\n".join([
        "read_lef /OpenROAD-flow-scripts/flow/platforms/nangate45/lef/NangateOpenCellLibrary.tech.lef",
        "read_lef /OpenROAD-flow-scripts/flow/platforms/nangate45/lef/NangateOpenCellLibrary.macro.mod.lef",
        f"read_liberty {{{liberty}}}", "read_verilog toy.v", "link_design toy", "read_spef toy.spef",
        "create_clock -name clk -period 3.333333 [get_ports clk]", "set_input_transition 0.05 [get_ports din]",
        "puts SETUP_BEGIN", "report_checks -path_delay max -digits 9 -fields {input_pins capacitance slew}",
        "puts HOLD_BEGIN", "report_checks -path_delay min -digits 9 -fields {input_pins capacitance slew}",
        "puts ELECTRICAL_BEGIN", "report_check_types -max_capacitance -max_slew -violators -digits 6",
        "puts END_TCL",
    ])+"\n")


def prepare(study, liberty, output, count):
    output.mkdir()
    direct, repaired, evidence = (read(study/f"{name}.json") for name in ("direct", "repair", "trials"))
    stage_by_pins = {(n["driver"], tuple(n["sinks"])): n["id"] for n in repaired["physical_spec"]["nets"]}
    inventory = {b["id"]: b for b in read(study/"inventory.json")["repeaters"]}
    wires = repaired["physical_routes"]["routes"]
    cases = []
    for row in evidence:
        name, selection = row["net"], row["selected"]
        if not selection or not row["direct_load"] or name not in direct["routes"]:
            continue
        original = direct["routes"][name]
        src, dst = [pin["pin"] for pin in original["via10"]]
        pick = inventory[selection]
        stages = [wires[stage_by_pins[pair]] for pair in
                  ((src, (pick["input"]["id"],)), (pick["output"]["id"], (dst,)))]
        trial = next(t for t in row["trials"] if t["relay"] == selection)
        if any(leg["over_ff"] for leg in trial["loads"]):
            continue
        for kind, routes in (("direct", [original]), ("buffered", stages)):
            case = output/f"{name}-{kind}"
            emit(case, liberty, routes, kind == "buffered")
        cases.append({"net": name, "driver": src, "sink": dst, "relay": selection,
                      "direct_wire_um": length(original)/2000,
                      "direct_load": row["direct_load"][0], "segments": trial})
        if len(cases) == count:
            break
    if not cases:
        raise ValueError("No comparable paired routes")
    (output/"cases.json").write_text(json.dumps(cases, indent=2)+"\n")


def summarize(output):
    result = read(output/"cases.json")
    for case in result:
        for mode in ("direct", "buffered"):
            report = (output/f"{case['net']}-{mode}"/"sta.log").read_text()
            if "END_TCL" not in report or re.search(r"^(?:Error:|\[ERROR)", report, re.M):
                raise ValueError(f"{case['net']} {mode}: invalid STA")
            setup, hold = report.split("SETUP_BEGIN")[1].split("ELECTRICAL_BEGIN")[0].split("HOLD_BEGIN")
            def slack(section):
                return 1000*float(re.search(r"([-+]?\d+\.\d+)\s+slack \((?:MET|VIOLATED)\)", section)[1])
            points = {}
            for pin in ("original_driver/Z", "relay/A", "relay/Z", "capture/D"):
                match = re.search(r"([-+]?\d+\.\d+)\s+[\^v]\s+"+re.escape(pin)+r"\s", setup)
                if match:
                    points[pin] = 1000*float(match[1])
            wanted = (("original_driver/Z", "capture/D"),) if mode == "direct" else (
                ("original_driver/Z", "relay/A"), ("relay/A", "relay/Z"), ("relay/Z", "capture/D"))
            case[mode] = {"setup_ps": slack(setup), "hold_ps": slack(hold),
                          "increments_ps": [points[b]-points[a] for a, b in wanted]}
    (output/"timing-summary.json").write_text(json.dumps(result, indent=2)+"\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    parser.add_argument("--study", type=Path)
    parser.add_argument("--liberty", type=Path)
    parser.add_argument("--count", type=int, default=4)
    args = parser.parse_args()
    if args.study:
        prepare(args.study.resolve(), args.liberty.resolve(), args.output.resolve(), args.count)
    else:
        summarize(args.output)
