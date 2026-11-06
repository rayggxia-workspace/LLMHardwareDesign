"""Build equivalent-native and stressed-load STA cases from accepted constraints."""
from pathlib import Path
import sys
kind=sys.argv[1]
local=Path.cwd()
base=Path(sys.argv[2])
ports=Path(sys.argv[3])
p=base/"issue-187-p16-j16/139-p-final-gates"
u=base/f"issue-188-ucf16/accepted-ucf16-01/{kind}16"
if kind=="P":
    lines=(p/"gates/P-electrical/hierarchy-sta.tcl").read_text().splitlines()
    result=[]
    for line in lines:
        if line.startswith("report_parasitic") or line.startswith("source "):
            continue
        if "parent-odb.v" in line:
            line=f"read_verilog {{{local/'eco-routed.v'}}}"
        if line.startswith("read_spef {"):
            line=f"read_spef {{{local/'candidate.spef'}}}"
        result.append(line)
else:
    standard="/OpenROAD-flow-scripts/flow/platforms/nangate45"
    result=[
        f"read_lef {standard}/lef/NangateOpenCellLibrary.tech.lef",
        f"read_lef {standard}/lef/NangateOpenCellLibrary.macro.mod.lef",
        f"read_lef {{{base/'issue-155/bank-views-011/generation/bank/s_sram_256x128_freepdk45.lef'}}}",
        f"read_liberty {standard}/lib/NangateOpenCellLibrary_typical.lib",
        f"read_liberty {{{u/'s_sram_256x128_freepdk45_TT_1p1V_25C.lib'}}}",
        f"read_verilog {{{local/'eco-routed.v'}}}",
        f"link_design -hier block_{kind.lower()}16",
        f"read_sdc {{{u/'6_final.sdc'}}}",
        f"read_spef {{{local/'candidate.spef'}}}",
        "set_propagated_clock [all_clocks]",
        "report_worst_slack -max -digits 6",
        "report_worst_slack -min -digits 6",
        "report_tns -digits 6",
        "report_check_types -violators -max_slew -max_capacitance -max_fanout -max_delay -min_delay -recovery -removal -min_period -min_pulse_width -digits 6 > electrical-violations.rpt",
        "check_setup -verbose > check-setup.rpt",
    ]
for stress in (False,True):
    text=[]
    for line in result:
        if stress and line.startswith("set_propagated_clock"):
            for entry in ports.read_text().splitlines():
                name,load=entry.split()
                text.append(f"set_load -pin_load {load} [get_ports {name}]")
        text.append(line.replace("electrical-violations.rpt",f"electrical-violations-{int(stress)}.rpt"))
    (local/f"sta-{int(stress)}.tcl").write_text("\n".join(text)+"\n")
