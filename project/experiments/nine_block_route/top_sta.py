"""Compose three ECO blocks for an ideal-parent-clock 300 MHz timing experiment."""
import json
from pathlib import Path
import re
import sys

base=Path(sys.argv[1]).resolve()
out=Path(sys.argv[2]).resolve()
out.mkdir()
route_path=Path(sys.argv[3]).resolve() if len(sys.argv)>3 else base.parent/"gds-97924-30/route.json"
source=route_path.parent if len(sys.argv)>3 else base.parent/"escape-97881-30"
shape=json.loads(route_path.read_text())["routes"]
blocks={"P0":Path(sys.argv[4]).resolve() if len(sys.argv)>4 else base/"eco-98042-0",
        "C0":Path(sys.argv[5]).resolve() if len(sys.argv)>5 else base/"eco-98057-1",
        "U0":base/"eco-98057-2"}
coupons={}
binding={}
for row in (source/"coupon.def").read_text().splitlines():
    m=re.match(r"^- (\w+) \( (\w+) (\S+) \) \( (\w+) (\S+) \) \+ USE SIGNAL ;$",row)
    if m:
        net,a,ap,b,bp=m.groups()
        assert (a,ap) not in binding and (b,bp) not in binding
        coupons[net]=(a,ap,b,bp)
        binding[a,ap]=net
        binding[b,bp]=net
assert set(coupons)==set(shape)
external={"clk":("input","")}
wires=set(coupons)
instances=[]
for instance,folder in blocks.items():
    rtl=(folder/"eco-routed.v").read_text()
    module=re.search(r"^module (\w+)",rtl,re.M)[1]
    links=[]
    for direction,span,port in re.findall(r"^\s*(input|output|inout)\s+(\[\d+:\d+\])?\s*(\w+)\s*;",rtl,re.M):
        if port=="clk":
            value="clk"
        else:
            indices=list(range(int(span[1:].split(":")[0]),int(span.split(":")[1][:-1])-1,-1)) if span else [None]
            mapped=[]
            for bit in indices:
                native=port if bit is None else f"{port}[{bit}]"
                value=binding.get((instance,native))
                if value is None:
                    value=instance+"_"+port+("" if bit is None else f"_{bit}")
                    external[value]=(direction,"")
                mapped.append(value)
            value=mapped[0] if not span else "{"+",".join(mapped)+"}"
        links.append(f"    .{port}({value})")
    instances.append(f"{module} {instance}(\n"+",\n".join(links)+"\n);")
for key,value in binding.items():
    if key[0]=="PIN":
        external[value]=("output","")
        wires.remove(value)
(out/"top.v").write_text("module nine_timing(\n"+",\n".join(external)+"\n);\n"+"\n".join(
    f"{d} {port};" for port,(d,_) in external.items())+"\n"+"\n".join(f"wire {w};" for w in sorted(wires))+
    "\n"+"\n".join(instances)+"\nendmodule\n")

for name,scale in (("low",.7),("high",1.5)):
    spef=["*SPEF \"IEEE 1481-1998\"",'*DESIGN "nine_timing"','*DATE "2026-11-06"',
          '*VENDOR "llhd"','*PROGRAM "coupon"','*VERSION "1"','*DESIGN_FLOW "PIN_CAP NONE"',
          "*DIVIDER /","*DELIMITER :","*BUS_DELIMITER []","*T_UNIT 1 NS","*C_UNIT 1 PF","*R_UNIT 1 OHM","*L_UNIT 1 HENRY"]
    for net,(a,ap,b,bp) in coupons.items():
        length=sum(abs(x-u)+abs(y-v) for _,(x,y),(u,v) in shape[net]["segments"])/2000
        c=scale*0.155390385*length/1000
        r=scale*(.015*length+.08*sum(len(shape[net][x]) for x in ("via10","via11")))
        near=f"{a}:{ap}"
        far=net if b=="PIN" else f"{b}:{bp}"
        nodes=[near,*[f"{net}:{i}" for i in range(1,4)],far]
        spef.extend([f"*D_NET {net} {c:.8f}","*CONN",f"*I {near} O",
                     f"*P {far} O" if b=="PIN" else f"*I {far} I","*CAP"])
        spef.extend(f"{i} {p} {c*(.125 if i in (1,5) else .25):.8f}" for i,p in enumerate(nodes,1))
        spef.append("*RES")
        spef.extend(f"{i} {p} {q} {r/4:.8f}" for i,(p,q) in enumerate(zip(nodes,nodes[1:]),1))
        spef.append("*END")
    (out/f"upper-{name}.spef").write_text("\n".join(spef)+"\n")

proj=base.parent.parent
native=proj/"issue-187-p16-j16"
pa=native/"139-p-final-gates/gates/P-electrical"
banks=proj/"issue-155/bank-views-011/generation/bank"
flow="/OpenROAD-flow-scripts/flow/platforms/nangate45"
for variant in ("low","high"):
    tcl=[f"read_lef {flow}/lef/NangateOpenCellLibrary.tech.lef",
         f"read_lef {flow}/lef/NangateOpenCellLibrary.macro.mod.lef",
         f"read_lef {{{banks/'s_sram_256x128_freepdk45.lef'}}}",
         f"read_liberty {flow}/lib/NangateOpenCellLibrary_typical.lib",
         f"read_liberty {{{banks/'s_sram_256x128_freepdk45_TT_1p1V_25C.lib'}}}",
         *(f"read_verilog {{{pa/(n+'-odb.v')}}}" for n in ("p4","M","G")),
         *(f"read_verilog {{{p/'eco-routed.v'}}}" for p in blocks.values()),
         f"read_verilog {{{out/'top.v'}}}","link_design -hier nine_timing",
         "create_clock -name core -period 3.333333333 [get_ports clk]",
         "set ext {}; foreach p [all_inputs] { if {[get_full_name $p] ne \"clk\"} { lappend ext $p } }",
         "set_clock_uncertainty .1 [get_clocks core]",
         "set_input_delay .8 -max -clock core $ext",
         "set_input_delay .2 -min -clock core $ext",
         "set_driving_cell -lib_cell BUF_X2 -pin Z $ext",
         "set_output_delay .8 -max -clock core [all_outputs]",
         "set_output_delay .2 -min -clock core [all_outputs]",
         f"read_spef {{{out/f'upper-{variant}.spef'}}}",
         *(f"read_spef -path {k} {{{p/'candidate.spef'}}}" for k,p in blocks.items()),
         *(f"read_spef -path P0/{inst} {{{native/'005-leaf-views/inputs'/m/'6_final.spef'}}}"
           for inst,m in (("store","p4"),("multiply","M"),("gate","G"))),
         "set_propagated_clock [all_clocks]",
         "report_worst_slack -max -digits 6","report_worst_slack -min -digits 6",
         'puts "COUPON_ELECTRICAL_BEGIN"',
         "report_check_types -violators -max_capacitance -max_slew -digits 6",
         'puts "COUPON_ELECTRICAL_END"',
         "report_parasitic_annotation",
         'puts "COUPON_NETS [llength [get_nets {p_gate_* C0_U0_* U0_C0_*}]]"',
         'set receivers [all_registers -data_pins]',
         'foreach pp {P0/m_to_g_data* P0/g_from_m_valid P0/m_to_g_take U0/tx_data* C0/tx_data* C0/tx_valid U0/tx_valid C0/rx_stored U0/rx_stored} {',
         '  set pin [get_pins $pp]; puts "REGISTERED_COUPON_GROUP $pp [llength $pin]"',
         '  if {[llength $pin] == 0} { error "coupon timing group has no pins: $pp" }',
         '  foreach mm {min max} {',
         '    puts "REGISTERED_COUPON_CHECK $pp $mm"',
         '    report_checks -through $pin -to $receivers -path_delay $mm -group_path_count 2 -digits 6 -format full_clock_expanded',
         '  }',
         '}',
         'puts "CONTROLLER_BOUNDARY_DIAGNOSTIC"',
         'report_checks -to [get_ports {C0_U0_ready U0_C0_ready C0_tx_ready U0_tx_ready}] -path_delay min_max -group_path_count 8 -digits 6 -format full_clock_expanded',
         "report_checks -path_delay min_max -group_path_count 4 -digits 6 -format full_clock_expanded",
         'puts "UPPER_CAPS_BEGIN"',
         'foreach n [get_nets {p_gate_* C0_U0_* U0_C0_*}] { report_net [get_full_name $n] }',
         'puts "UPPER_CAPS_END"']
    (out/f"sta-{variant}.tcl").write_text("\n".join(tcl)+"\n")
