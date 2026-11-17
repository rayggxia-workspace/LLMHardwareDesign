from pathlib import Path
import re
root=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117');gs=root/'gs';src=gs/'candidate-S-minimal-localv4/parent-F-eco-h20-v4-repair3';out=src.with_name(src.name+'-graft');out.mkdir();(out/'config.mk').write_bytes((src/'config.mk').read_bytes());old=(gs/'f-eco-v4.tcl').read_text();defs=old[old.index('proc boundary {}'):old.index('# DEF encodes')];libs=re.search(r'^export ADDITIONAL_LIBS = (.*)$',(src/'config.mk').read_text(),re.M)[1].split()
body='set_thread_count 8\nset platform /OpenROAD-flow-scripts/flow/platforms/nangate45\nread_liberty $platform/lib/NangateOpenCellLibrary_typical.lib\n'+''.join('read_liberty {'+p+'}\n' for p in libs)+f'read_db {{{src}/candidate.odb}}\nread_sdc {{{src}/candidate.sdc}}\nset_propagated_clock [all_clocks]\nset block [ord::get_db_block]\n'+defs+'set old_boundary [boundary]\nset old_macros [macro_positions]\n'
body+='''set donor [odb::dbDatabase_create]
odb::read_db $donor /public/home/yuzelu/project-circuit/main-blockv2-f300-side-01/flow/results/nangate45/f-native-frame/base/6_final.odb
set db [[$donor getChip] getBlock]
proc pin_shapes {net} {
 set result {}
 foreach it [$net getITerms] {
  foreach geom [$it getGeometries] {
   lassign $geom layer rect
   lappend result [list [[$it getInst] getName] [[$it getMTerm] getName] [$layer getName] [$rect xMin] [$rect yMin] [$rect xMax] [$rect yMax]]
  }
 }
 return [lsort $result]
}
'''
names=sorted(set(re.findall(r'net:(\S+)', '\n'.join(x for x in (src/'native-drc.rpt').read_text().split('violation type:') if 'metal10' in x))))
for name in names:
 body+=f'set n [$block findNet {{{name}}}]\nset s [$db findNet {{{name}}}]\nif {{$n eq "NULL" || $s eq "NULL"}} {{error "Missing graft net"}}\nif {{[net_signature $n] ne [net_signature $s] || [pin_shapes $n] ne [pin_shapes $s]}} {{error "Graft endpoint geometry differs: {name}"}}\nset dw [$s getWire]\nif {{$dw eq "NULL"}} {{error "Donor unrouted"}}\nodb::dbWire_destroy [$n getWire]\nset w [odb::dbWire_create $n]\n$w append $dw\nif {{[$w count] != [$dw count]}} {{error "Graft incomplete"}}\nputs {{EXACT_GRAFT {name}}}\n'
body+=old[old.index('if {[boundary] ne $old_boundary || [macro_positions] ne $old_macros}'):];(out/'repair.tcl').write_text(body)
