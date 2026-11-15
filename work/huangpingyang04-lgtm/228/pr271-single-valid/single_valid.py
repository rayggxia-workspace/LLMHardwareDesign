"""One-net comparison on the original #271 A interface handoff."""
from hashlib import sha256
import json
from pathlib import Path
import re
import sys

from check import digest
from geometry import access_points, box, touching
from handoff import verify_handoff
from repair import repair
from repeaters import check_allocations, physical_nets
import resource_search as search


SOURCE = "U0/dma_req_valid"
TARGET = "dma/c_req_valid[3]"
SINKS = [("NAND3_X1", "A1"), ("NAND3_X1", "A1"), ("NAND2_X1", "A1"),
         ("AOI21_X1", "B1"), ("AOI21_X1", "B1"), ("NOR4_X1", "A2")]
SCALE = 2000
WIRE_CAP = 0.155390385 * 1.5
WIRE_RES = 0.015 * 1.5
VIA_CAP = 0.2
VIA_RES = 0.08 * 1.5


def read(path):
    return json.loads(path.read_text())


def save(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n")


def prop(cell, pin, field):
    cell_parts = re.split(r"\n\s*cell\s*\(\s*" + cell + r"\s*\)\s*\{", LIB, maxsplit=1)
    body = re.split(r"\n\s*cell\s*\(", cell_parts[1], maxsplit=1)[0]
    pin_body = re.split(r"\n\s*pin\s*\(\s*" + pin + r"\s*\)\s*\{", body, maxsplit=1)[1]
    pin_body = re.split(r"\n\s*pin\s*\(", pin_body, maxsplit=1)[0]
    return float(re.search(r"\b" + field + r"\s*:\s*([\d.eE+-]+)", pin_body)[1])


def inventory(spec, placement):
    tech, pins = spec["technology"], spec["pins"]
    sx, sy = access_points(pins[SOURCE], tech)[0]
    blocks = list(placement["boxes_dbu"].values())
    cap_in = prop("BUF_X32", "A", "capacitance")
    cap_out = prop("BUF_X32", "Z", "max_capacitance")
    native_pins = [r for shapes in pins.values() for r in shapes]
    pitch = tech["pitch"]
    sites = []
    for i, (dx, dy) in enumerate(((0, -2), (1, -6), (2, -12), (8, -16), (16, -24), (30, -30), (50, -40),
                                  (260, -28), (430, -35), (540, -43), (650, -52))):
        bx = tech["origin"][0] + round((sx-tech["origin"][0])/pitch)*pitch + dx*pitch
        by = tech["origin"][1] + round((sy-tech["origin"][1])/pitch)*pitch + dy*pitch
        a, z = (bx, by), (bx+2*pitch, by)
        footprint = [bx-2400, by-2400, z[0]+2400, by+2400]
        if any(touching(footprint, rect) for rect in (*blocks, *native_pins)):
            continue
        name = "gap-{:02d}".format(i+1)
        sites.append({"id": name, "status": "virtual", "power": "assumed", "footprint_dbu": footprint,
                      "input": {"id": name+"/A", "m10": [list(box(a, 4000))]},
                      "output": {"id": name+"/Z", "m10": [list(box(z, 4000))]},
                      "input_cap_ff": cap_in, "output_limit_ff": cap_out})
    return {"schema_version": "upper-repeaters/1", "units": "dbu", "dbu_per_micron": SCALE,
            "native_keepouts": blocks, "repeaters": sites,
            "electrical": {"wire_cap_ff_per_dbu": WIRE_CAP/SCALE, "via10_cap_ff": VIA_CAP,
                           "via11_cap_ff": VIA_CAP,
                           "driver_limits_ff": {SOURCE: prop("AND2_X1", "ZN", "max_capacitance")
                                                - prop("AND2_X1", "A2", "capacitance")},
                           "sink_caps_ff": {TARGET: sum(prop(c, p, "capacitance") for c, p in SINKS)}}}


def geometry(route):
    um = search.length(route) / SCALE
    cuts = len(route["via10"]) + len(route["via11"])
    return {"length_um": um, "vias": cuts, "wire_cap_ff": um*WIRE_CAP+cuts*VIA_CAP,
            "wire_res_ohm": um*WIRE_RES+cuts*VIA_RES, "via10": route["via10"]}


def spef_net(name, src, target, route):
    stats = geometry(route)
    cap = stats["wire_cap_ff"] / 1000
    res = stats["wire_res_ohm"]
    nodes = [src, *(name+":{}".format(i) for i in range(1, 4)), target]
    return "\n".join([f"*D_NET {name} {cap:.9f}", "*CONN", f"*I {src} O", f"*P {target} O", "*CAP",
                      *(f"{i} {n} {cap*w:.9f}" for i, (n,w) in
                        enumerate(zip(nodes, (.125,.25,.25,.25,.125)), 1)),
                      "*RES", *(f"{i} {a} {b} {res/4:.9f}" for i,(a,b) in
                                enumerate(zip(nodes,nodes[1:]),1)), "*END"])


def write_sta(folder, routes):
    folder.mkdir()
    buffered = len(routes) == 2
    orig = "head" if buffered else "arrived"
    lines = ["module toy(input clk,din,enable,ready,output arrived,local_use);", "wire q,head;",
             "DFF_X1 launch(.D(din),.CK(clk),.Q(q),.QN());",
             f"AND2_X1 src(.A1(q),.A2(enable),.ZN({orig}));",
             f"AND2_X1 tap(.A1(ready),.A2({orig}),.ZN(local_use));"]
    if buffered:
        lines.append("BUF_X32 relay(.A(head),.Z(arrived));")
    (folder/"toy.v").write_text("\n".join(lines+["endmodule", ""]))
    sections = ['*SPEF "IEEE 1481-1998"', '*DESIGN "toy"', '*DATE "2026-11-15"',
                '*VENDOR "LLMHardwareDesign"', '*PROGRAM "Algorithm 2 geometry RC"',
                '*VERSION "1"', '*DESIGN_FLOW "PIN_CAP NONE"', '*DIVIDER /', '*DELIMITER :',
                '*BUS_DELIMITER [ ]', '*T_UNIT 1 NS', '*C_UNIT 1 PF', '*R_UNIT 1 OHM', '*L_UNIT 1 HENRY']
    if buffered:
        pre = spef_net("head", "src:ZN", "relay:A", routes[0]).replace("*P relay:A O", "*I relay:A I")
        sections.extend([pre.replace("*I relay:A I", "*I relay:A I\n*I tap:A2 I"),
                         spef_net("arrived", "relay:Z", "arrived", routes[1])])
    else:
        sections.append(spef_net("arrived", "src:ZN", "arrived", routes[0]).replace(
            "*P arrived O", "*P arrived O\n*I tap:A2 I"))
    # The local tap is at the driver node in this interface model.
    sections = [section.replace("*RES\n1 src:ZN", "*RES\n5 src:ZN tap:A2 0.000001000\n1 src:ZN")
                for section in sections]
    (folder/"toy.spef").write_text("\n".join(sections)+"\n")
    platform = "/OpenROAD-flow-scripts/flow/platforms/nangate45/"
    sink_cap = sum(prop(c,p,"capacitance") for c,p in SINKS)
    (folder/"sta.tcl").write_text("\n".join([
        "read_lef "+platform+"lef/NangateOpenCellLibrary.tech.lef",
        "read_lef "+platform+"lef/NangateOpenCellLibrary.macro.mod.lef",
        "read_liberty {"+str(LIB_PATH)+"}", "read_verilog toy.v", "link_design toy",
        "read_spef toy.spef", "set_cmd_units -time ns -capacitance fF",
        "create_clock -name core -period 3.333333333 [get_ports clk]",
        "set_clock_transition 0.05 [get_clocks core]",
        "set_case_analysis 1 [get_ports enable]",
        f"set_load -pin_load {sink_cap} [get_ports arrived]",
        "set_output_delay -max 2.833333333 -clock core [get_ports arrived]",
        "puts ARRIVAL",
        "report_checks -from [get_pins launch/Q] -to [get_ports arrived] -path_delay max -format full_clock_expanded -fields {input_pins capacitance slew} -digits 9",
        "puts ELECTRICAL",
        "report_check_types -max_capacitance -max_slew -violators -digits 9",
        "puts END_STA", ""
    ]))


def sta_value(log):
    arrival, electrical = log.split("ARRIVAL\n")[1].split("ELECTRICAL\n")
    if "END_STA" not in electrical or re.search(r"^(?:Error|\[ERROR)", log, re.M):
        raise ValueError("OpenSTA did not complete")
    result = {}
    for term in ("data arrival time", "data required time", "slack"):
        result[term] = 1000*float(re.search(r"([-\d.]+)\s+"+term, arrival)[1])
    for name in ("src/ZN", "relay/A", "relay/Z", "arrived"):
        match = re.search(r"([-\d.]+)\s+[\^v]\s+"+name+r"\s", arrival)
        if match:
            result[name] = 1000*float(match[1])
    result["capacitance_violated"] = "max capacitance" in electrical
    result["slew_violated"] = "max slew" in electrical
    cap = re.search(r"src/ZN\s+([\d.]+)\s+([\d.]+)\s+[-\d.]+\s+\(VIOLATED\)", electrical.split("max capacitance")[-1])
    if cap and result["capacitance_violated"]:
        result["limit_ff"], result["measured_ff"] = map(float,cap.groups())
    return result


def main():
    step, handoff, *_ = sys.argv[1:]
    handoff = Path(handoff)
    full = read(handoff/"algorithm2-input.json")
    net, = [r for r in full["nets"] if (r["driver"],r["sinks"]) == (SOURCE,[TARGET])]
    spec = dict(full, nets=[net])
    data = inventory(spec, read(handoff.parent/"placement.json"))
    budget = int(sys.argv[4]) if len(sys.argv)>4 else 240000
    options = {"rounds": 1, "max_expansions": budget, "candidate_limit": 8}
    # Enable a verified-geometry macro move only in the optional fallback.
    if len(sys.argv)>5 and sys.argv[5] in ("jumps", "fast"):
        import weighted
        weighted.enable(1 if sys.argv[5] == "jumps" else 4, True)
    if step == "direct":
        verify_handoff(full, handoff)
        save(Path("spec.json"),spec)
        save(Path("inventory.json"),data)
        print("direct", net, len(data["repeaters"]), flush=True)
        direct = search.route_resources(spec,data,max_repeaters=0,**options)
        save(Path("direct.json"),direct)
        if direct["failed"]:
            raise ValueError(direct["failed"])
        write_sta(Path("direct"), list(direct["physical_routes"]["routes"].values()))
    elif step == "buffer":
        direct = read(Path("direct.json"))
        baseline = sta_value(Path("direct/sta.log").read_text())
        if not baseline["capacitance_violated"] or baseline["measured_ff"] <= baseline["limit_ff"]:
            raise ValueError("Direct did not violate max capacitance")
        feedback = {"schema_version": "upper-route-feedback/1",
                    "route_sha256": digest(direct["physical_routes"]),
                    "evidence": "direct/sta.log#ELECTRICAL",
                    "violations": [{"segment": "segment/0/0", "metric": "capacitance",
                                    "measured": baseline["measured_ff"], "limit": baseline["limit_ff"]}]}
        save(Path("feedback.json"),feedback)
        pins,resources = search.inventory(spec,data)
        ranked = list(search.choices(net,pins,resources,options["candidate_limit"],1))[1:]
        save(Path("candidate-order.json"),ranked)
        for option in ranked:
            print("candidate", option["repeater"], flush=True)
        result=repair(spec,data,direct,feedback,max_repeaters=1,**options)
        save(Path("buffered.json"),result)
        if result["failed"] or not result["allocations"][net["id"]]:
            raise ValueError("No valid repeater repair")
        check_allocations(spec,data,result)
        stages=physical_nets(net,0,result["allocations"][net["id"]],resources)
        print("selected", result["allocations"][net["id"]], flush=True)
        write_sta(Path("buffered"),[result["physical_routes"]["routes"][st["id"]] for st in stages])
    else:
        ds=sta_value(Path("direct/sta.log").read_text())
        bs=sta_value(Path("buffered/sta.log").read_text())
        d,b=(read(Path(f"{name}.json")) for name in ("direct","buffered"))
        result={"net":net,"source_m10_dbu":spec["pins"][SOURCE],"sink_m10_dbu":spec["pins"][TARGET],
                "allocation":b["allocations"][net["id"]],"estimated_stage_loads":b["estimated_stage_loads"],
                "direct":ds,"buffered":bs,
                "timing_improvement_ps":ds["data arrival time"]-bs["data arrival time"],
                "buffered_segment_delays_ps":[bs["relay/A"]-bs["src/ZN"],bs["relay/Z"]-bs["relay/A"],
                                               bs["arrived"]-bs["relay/Z"]],
                "direct_net_delay_ps":ds["arrived"]-ds["src/ZN"],
                "geometry":{k:[geometry(r) for r in v["physical_routes"]["routes"].values()]
                            for k,v in (("direct",d),("buffered",b))},
                "input_sha256":sha256((handoff/"algorithm2-input.json").read_bytes()).hexdigest()}
        save(Path("summary.json"),result)
        print(json.dumps(result,indent=2))


if __name__ == "__main__":
    LIB_PATH=Path(sys.argv[3]).resolve()
    LIB=LIB_PATH.read_text()
    main()
