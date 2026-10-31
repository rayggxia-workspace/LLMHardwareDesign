# Read-only diagnostic of all hold failures on one immutable actual-RC design.
set_thread_count 16
set platform /OpenROAD-flow-scripts/flow/platforms/nangate45
read_liberty $platform/lib/NangateOpenCellLibrary_typical.lib
read_db $::env(BV1_ODB)
read_sdc $::env(BV1_SDC)
read_spef $::env(BV1_SPEF)
set_propagated_clock [all_clocks]
sta::find_timing
report_checks -path_delay min -slack_max 0 -group_path_count 10000 -endpoint_path_count 1 -digits 9 -format full_clock_expanded > all-hold.rpt
set stream [open all-hold.rpt r]
set content [read $stream]
close $stream
set endpoints [dict create]
foreach {line endpoint} [regexp -all -inline -line {^Endpoint: (\S+)} $content] {
 if {[dict exists $endpoints $endpoint]} {error "Duplicate reported hold endpoint"}
 dict set endpoints $endpoint 1
}
if {[dict size $endpoints] != [sta::endpoint_violation_count min]} {error "Hold report omitted failing endpoints"}
set block [ord::get_db_block]
set stream [open endpoint-index.tsv w]
puts $stream "index\tendpoint\tmaster\tdata_net"
set number 0
dict for {endpoint ignored} $endpoints {
 set inst [$block findInst $endpoint]
 if {$inst eq "NULL" || $inst eq ""} {error "Hold endpoint not found in actual ODB"}
 set term [$inst findITerm D]
 if {$term eq "NULL" || $term eq "" || [[$term getMTerm] getIoType] ne "INPUT"} {error "Hold endpoint data pin missing"}
 set pin [get_pins [list ${endpoint}/D]]
 if {[llength $pin] != 1} {error "Hold endpoint STA pin missing"}
 puts $stream "$number\t$endpoint\t[[$inst getMaster] getName]\t[[$term getNet] getName]"
 report_checks -path_delay max -to $pin -group_path_count 1 -digits 9 -format full_clock_expanded > endpoint-setup-$number.rpt
 incr number
}
close $stream
set f [open summary.tsv w]
puts $f "diagnostic_only\ttrue"
puts $f "native_leaf_accepted\tfalse"
puts $f "setup_checks\t[sta::endpoint_violation_count max]"
puts $f "hold_checks\t[sta::endpoint_violation_count min]"
close $f
report_worst_slack -max -digits 9 > timing.rpt
report_worst_slack -min -digits 9 >> timing.rpt
