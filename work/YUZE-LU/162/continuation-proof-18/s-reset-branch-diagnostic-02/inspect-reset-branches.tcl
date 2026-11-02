set_thread_count 16
read_liberty {/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib}
read_db {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/s-internal-drive-02/candidate-1182/flow/results/nangate45/bv1_block_feed_s_macro/base/5_1_grt.odb}
read_sdc {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/s-internal-drive-02/candidate-1182/flow/results/nangate45/bv1_block_feed_s_macro/base/5_1_grt.sdc}
source {/OpenROAD-flow-scripts/flow/platforms/nangate45/setRC.tcl}
estimate_parasitics -placement

set block [ord::get_db_block]
if {[$block getName] ne "block_feed_s_macro"} {error "S diagnostic scope mismatch"}
set reset [$block findBTerm reset]
if {$reset eq "NULL" || [$reset getIoType] ne "INPUT"} {error "Missing actual S reset input"}
set todo [list [list [$reset getNet] 0]]
set visited [dict create];set branches {};set buffers {}
while {[llength $todo]} {
 lassign [lindex $todo 0] net depth;set todo [lrange $todo 1 end]
 if {[dict exists $visited [$net getName]]} {continue}
 if {[dict size $visited]>=4096} {error "Reset diagnostic unique-net inventory exceeds4096 at depth $depth"}
 dict set visited [$net getName] 1
 foreach pin [$net getITerms] {
  if {[[$pin getMTerm] getSigType] in {POWER GROUND} || [[$pin getMTerm] getIoType] ne "INPUT"} {continue}
  set inst [$pin getInst];set master [[$inst getMaster] getName]
  if {[regexp {^(BUF|CLKBUF)_X[0-9]+$} $master]} {
   set outputs {}
   foreach term [$inst getITerms] {
    if {[[$term getMTerm] getSigType] ni {POWER GROUND} && [[$term getMTerm] getIoType] eq "OUTPUT"} {lappend outputs $term}
   }
   if {[llength $outputs]!=1} {error "Reset buffer output identity"}
   lappend buffers [list [$inst getName] $master [$net getName]]
   lappend todo [list [[lindex $outputs 0] getNet] [expr {$depth+1}]]
  } else {
   lappend branches [list [$inst getName] [[$pin getMTerm] getName] $master [$net getName]]
  }
 }
}
if {![llength $branches] || [llength $branches]>128} {error "Unbounded or absent reset branches"}
set f [open reset-buffer-cone.tsv w]
foreach row $buffers {puts $f [join $row "\t"]};close $f
set f [open reset-branches.tsv w];set index 0
foreach row $branches {
 lassign $row inst term master net
 set pin [get_pins [list ${inst}/$term]]
 if {[llength $pin]!=1} {error "Actual reset branch STA pin missing"}
 puts $f [join [linsert $row 0 $index] "\t"]
 foreach kind {min max} {
  report_checks -from [get_ports reset] -through $pin -path_delay $kind -group_path_count 8 -format full_clock_expanded -fields {slew cap fanout input net} -digits 9 > branch-$index-$kind.rpt
 }
 incr index
}
close $f
report_checks -from [get_ports reset] -path_delay min -group_path_count 128 -format full_clock_expanded -fields {slew cap fanout input net} -digits 9 > reset-min.rpt
report_check_types -max_capacitance -max_slew -violators -digits 9 > electrical.rpt
report_worst_slack -max
report_worst_slack -min
