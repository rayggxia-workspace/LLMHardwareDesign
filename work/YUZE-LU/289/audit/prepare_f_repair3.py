from pathlib import Path
import re
root=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117');gs=root/'gs';src=gs/'candidate-S-minimal-localv4/parent-F-eco-h20-v4-repair2';out=src.with_name('parent-F-eco-h20-v4-repair3');out.mkdir();(out/'config.mk').write_text((src/'config.mk').read_text())
old=(gs/'f-eco-v4.tcl').read_text();defs=old[old.index('proc boundary {}'):old.index('# DEF encodes')]
libs=re.search(r'^export ADDITIONAL_LIBS = (.*)$',(src/'config.mk').read_text(),re.M)[1].split()
body='set_thread_count 8\nset platform /OpenROAD-flow-scripts/flow/platforms/nangate45\nread_liberty $platform/lib/NangateOpenCellLibrary_typical.lib\n'+''.join('read_liberty {'+x+'}\n' for x in libs)
body+=f'read_db {{{src}/candidate.odb}}\nread_sdc {{{src}/candidate.sdc}}\nset_propagated_clock [all_clocks]\nset block [ord::get_db_block]\n'+defs+'set old_boundary [boundary]\nset old_macros [macro_positions]\nremove_fillers\n'
names=sorted(set(re.findall(r'net:(\S+)',(src/'native-drc.rpt').read_text())))
(out/'target-nets.txt').write_text('\n'.join(names)+'\n')
for n in names:
 assert '{' not in n and '}' not in n
 body+=f'set n [$block findNet {{{n}}}]\nif {{$n eq "NULL"}} {{error "Unknown repair net"}}\nset w [$n getWire]\nif {{$w ne "NULL"}} {{odb::dbWire_destroy $w}}\n'
body+='''foreach n [$block getNets] {
 if {[$n getSigType] in {POWER GROUND}} {continue}
 set hit 0
 foreach it [$n getITerms] {if {[[$it getInst] getName] eq {local_group.services.store.leaf}} {set hit 1}}
 if {$hit} {set w [$n getWire];if {$w ne "NULL"} {odb::dbWire_destroy $w}}
}
'''
body+=old[old.index('set_routing_layers -signal metal1-metal10 -clock metal1-metal10',old.index('close $f\nset_routing_layers')):]
(out/'repair.tcl').write_text(body)
