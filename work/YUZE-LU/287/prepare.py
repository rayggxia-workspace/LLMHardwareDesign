import json, pathlib, re, hashlib
P=pathlib.Path
root=P(__file__).resolve().parent
c=P('/public/home/yuzelu/project-circuit/issue250-c-frame-data-boot-cap-eco-20261112-03')
u=P('/public/home/yuzelu/project-circuit/issue250-u39-on-u38-exact-incremental-route-20261113-02-paired-escape-metal-mask-eco01-well-eco02')
std='/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib'
clibs=re.search(r'^export ADDITIONAL_LIBS = (.*)$',(c/'parent/config.mk').read_text(),re.M)[1].split()
ulibs=re.findall(r'read_liberty \{(.*?)\}',(u/'route-lib.tcl').read_text())
configs={
 'C':dict(odb=str(c/'flow/results/nangate45/c-native-frame/base/6_final.odb'),spef=str(c/'flow/results/nangate45/c-native-frame/base/6_final.spef'),sdc=str(c/'flow/results/nangate45/c-native-frame/base/6_final.sdc'),v=str(c/'flow/results/nangate45/c-native-frame/base/6_final.v'),libs=[std]+clibs),
 'U':dict(odb=str(u/'native-filled.odb'),spef=str(u/'native.spef'),sdc=str(u/'native.sdc'),v=str(u/'native-filled.v'),libs=ulibs)}
for name,cfg in configs.items():
 out=root/(name+'-v2');out.mkdir(exist_ok=True)
 cfg['sha256']={k:hashlib.sha256(P(cfg[k]).read_bytes()).hexdigest() for k in ('odb','spef','sdc','v')}
 text='\n'.join('read_liberty {'+s+'}' for s in cfg['libs'])+'\n'
 text+='read_db {'+cfg['odb']+'}\nread_sdc {'+cfg['sdc']+'}\nread_spef {'+cfg['spef']+'}\nset_propagated_clock [all_clocks]\n'
 text+='''report_worst_slack -max -digits 9 > setup.rpt
report_worst_slack -min -digits 9 > hold.rpt
report_units
report_checks -path_delay min_max -format full_clock_expanded -fields {slew capacitance input_pin net} -group_path_count 10 -digits 9 > paths.rpt
report_parasitic_annotation -report_unannotated > annotation.rpt
check_setup -verbose > constraints.rpt
foreach check {max_capacitance max_slew max_fanout} {
 report_check_types -$check -format end -max_count 200 -digits 9 > $check.rpt
}
write_verilog exported.v
set f [open ports.tsv w]
puts $f "port\tdirection\tnet\tcell\tmaster\tpin\tpin_direction"
foreach b [[ord::get_db_block] getBTerms] {
 set net [$b getNet]
 if {$net eq "NULL"} {continue}
 foreach it [$net getITerms] {
 set inst [$it getInst]
 set mt [$it getMTerm]
 puts $f "[$b getName]\\t[$b getIoType]\\t[$net getName]\\t[$inst getName]\\t[[$inst getMaster] getName]\\t[$mt getName]\\t[$mt getIoType]"
 }
}
close $f
puts BASELINE_COMPLETE
'''
 (out/'baseline.tcl').write_text(text)
(root/'inputs.json').write_text(json.dumps(configs,indent=2))

