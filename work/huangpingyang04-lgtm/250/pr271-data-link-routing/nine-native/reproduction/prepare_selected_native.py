"""Route the requested native port nets, then merge them into the intact DB."""
from pathlib import Path
import json
import sys
root=Path(sys.argv[1]).resolve();checked=Path(sys.argv[2]).resolve()
contacts=json.loads((checked/'native-expected-contacts.json').read_text())
for kind,block,source in [('C','C0',root/'C/native-contacts.odb'),('P','P2',root/'P-west/place250/placed.odb')]:
    out=root/f'native-final-{kind}';out.mkdir();(out/'tmp').mkdir()
    ports={p.split('.',1)[1]:b for p,b in contacts.items() if p.startswith(block+'.')}
    with (out/'route.tcl').open('w') as f:
        f.write('set_thread_count $::env(SLURM_CPUS_PER_TASK)\nset p /OpenROAD-flow-scripts/flow/platforms/nangate45\nread_liberty $p/lib/NangateOpenCellLibrary_typical.lib\n')
        if kind=='C':
            libs=next(l for l in (root/'C/config.mk').read_text().splitlines() if l.startswith('export ADDITIONAL_LIBS =')).split('=',1)[1].split()
            for lib in libs:f.write(f'read_liberty {{{lib}}}\n')
        else:
            for l in (root/'P/place250/place.tcl').read_text().splitlines():
                if l.startswith('read_liberty ') and 'Nangate' not in l:f.write(l+'\n')
        f.write(f'read_db {{{source}}}\nset b [ord::get_db_block]\nset db [ord::get_db]\nset tech [ord::get_db_tech]\nset selected {{}}\nset selected_ports {{}}\n')
        for name,box in ports.items():
            f.write('set term [$b findBTerm {'+name+'}]\nif {$term eq "NULL"} {error {Missing native port '+name+'}}\n')
            f.write('foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}\nset pin [odb::dbBPin_create $term]\n$pin setPlacementStatus FIRM\n')
            f.write('odb::dbBox_create $pin [$tech findLayer metal10] '+' '.join(map(str,box))+'\n')
            f.write('lappend selected_ports {'+name+'}\n')
        f.write('''set tie_index 0
foreach name $selected_ports {
 set term [$b findBTerm $name]
 set net [$term getNet]
 if {[$net getName] in {zero_ one_}} {
  if {[$term getIoType] ne "OUTPUT"} {error "Unexpected constant input port"}
  set master [expr {[$net getName] eq "zero_" ? "LOGIC0_X1" : "LOGIC1_X1"}]
  set tie [odb::dbInst_create $b [$db findMaster $master] NATIVE_PORT_TIE_$tie_index]
  $tie setLocation 2400000 [expr {1400000+$tie_index*5600}]
  $tie setPlacementStatus PLACED
  set split [odb::dbNet_create $b NATIVE_PORT_CONST_$tie_index]
  $split setSigType SIGNAL
  [$tie findITerm Z] connect $split
  $term disconnect
  $term connect $split
  incr tie_index
 }
 lappend selected [[$term getNet] getName]
}
if {$tie_index} {detailed_placement; check_placement}
foreach net [$b getNets] {
 if {[$net getSigType] in {POWER GROUND}} {$net setSpecial}
}
write_db full-native.odb
set gc [$b getGCellGrid]
if {$gc ne "NULL"} {odb::dbGCellGrid_destroy $gc}
# The routing scratch DB keeps physical obstacles, cells and power conductors.
# The full native connectivity is retained in full-native.odb and restored below.
foreach term [$b getBTerms] {
 if {[$term getName] ni $selected_ports && [$term getSigType] ni {POWER GROUND}} {odb::dbBTerm_destroy $term}
}
foreach net [$b getNets] {
 if {[$net getName] ni $selected && [$net getSigType] ni {POWER GROUND}} {odb::dbNet_destroy $net}
}
set_routing_layers -signal metal2-metal10 -clock metal2-metal10
set_global_routing_layer_adjustment metal2-metal10 0.10
global_route -guide_file native.guide -allow_congestion -congestion_iterations 5
detailed_route -output_drc native.drc -droute_end_iter 24 -via_in_pin_bottom_layer metal10 -via_in_pin_top_layer metal10 -via_access_layer metal10
write_db routed-subset.odb
write_def routed-subset.def
set f [open selected-nets.txt w]
foreach n [lsort -unique $selected] {puts $f $n}
close $f
''')
    (out/'merge.tcl').write_text('''read_db full-native.odb
proc connectivity {} {
 set rows {}
 foreach n [[ord::get_db_block] getNets] {
  set pins {}
  foreach t [$n getITerms] {lappend pins [list I [[$t getInst] getName] [[$t getMTerm] getName]]}
  foreach t [$n getBTerms] {lappend pins [list B [$t getName]]}
  lappend rows [list [$n getName] [lsort $pins]]
 }
 return [lsort $rows]
}
set before [connectivity]
read_def -incremental routed-subset.def
if {$before ne [connectivity]} {error "Native netlist changed during selected-route merge"}
write_db native-final.odb
write_def native-final.def
set f [open merge-receipt.txt w]
puts $f "PASS: complete native netlist preserved exactly across selected-route DEF merge"
puts $f "native_nets [llength $before]"
close $f
''')
    (out/'run.sh').write_text('''#!/bin/bash
#SBATCH --job-name=hpy-native-ports
#SBATCH --partition=debug,c64,c96
#SBATCH --cpus-per-task=16
#SBATCH --time=00:25:00
set -euo pipefail
export TMPDIR="$PWD/tmp" XDG_CACHE_HOME="$PWD/tmp" PYTHONDONTWRITEBYTECODE=1
tool=/public/home/yuzelu/project-circuit/issue185-joint-packet-dma-bound-20261113-01/tool.sh
bash "$tool" openroad -no_init -exit route.tcl > route.log 2>&1
test -s routed-subset.odb
bash "$tool" openroad -no_init -exit merge.tcl > merge.log 2>&1
''')
    print('Prepared selected native route',kind,len(ports),flush=True)
