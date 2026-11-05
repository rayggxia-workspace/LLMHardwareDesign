set_thread_count 16
read_liberty {/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib}
read_db {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/s-internal-drive-02/candidate-1182/flow/results/nangate45/bv1_block_feed_s_macro/base/5_1_grt.odb}
read_sdc {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/s-internal-drive-02/candidate-1182/flow/results/nangate45/bv1_block_feed_s_macro/base/5_1_grt.sdc}
source {/OpenROAD-flow-scripts/flow/platforms/nangate45/setRC.tcl}
estimate_parasitics -placement
set reset_anchors {{feed_input_receiver_174 BUF_X8} {input175 BUF_X8}}

set block [ord::get_db_block]
if {[$block getName] ne "block_feed_s_macro"} {error "S diagnostic scope mismatch"}
set reset [$block findBTerm reset]
if {$reset eq "NULL" || [$reset getIoType] ne "INPUT"} {error "Missing actual S reset input"}
set net [$reset getNet];set buffers {};set branches {}
foreach row $reset_anchors {
 lassign $row name master;set inst [$block findInst $name]
 if {$inst eq "NULL" || [[$inst getMaster] getName] ne $master} {error "Actual reset anchor identity changed"}
 set input [$inst findITerm A];set output [$inst findITerm Z]
 if {$input eq "NULL" || $output eq "NULL" || [$input getNet] ne $net} {error "Actual reset anchor chain disconnected"}
 lappend buffers [list $name $master [$net getName]];set net [$output getNet]
}
foreach pin [$net getITerms] {
 if {[[$pin getMTerm] getSigType] in {POWER GROUND} || [[$pin getMTerm] getIoType] ne "INPUT"} {continue}
 set inst [$pin getInst]
 lappend branches [list [$inst getName] [[$pin getMTerm] getName] [[$inst getMaster] getName] [$net getName]]
}
if {![llength $branches] || [llength $branches]>128} {error "Unbounded or absent reset branches"}
set f [open reset-buffer-anchors.tsv w]
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
