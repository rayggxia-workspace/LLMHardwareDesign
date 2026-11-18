read_liberty /OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib
foreach lib $::env(CU_LIBS) {read_liberty $lib}
set res $::env(CU_RESULTS)
set out $::env(CU_SIGNOFF)
read_db $res/6_final.odb
read_sdc $res/6_final.sdc
read_spef $res/6_final.spef
set_propagated_clock [all_clocks]
source /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/geometry.tcl
geometry_snapshot $out/geometry-final.tsv
set f [open $res/geometry-before.tsv];set before [read $f];close $f
set f [open $out/geometry-final.tsv];set after [read $f];close $f
if {$before ne $after} {error "Die/BPin/macro geometry changed"}
set b [ord::get_db_block]
set kind [dict get [dict create cfj_group_c_memory_legacy C u_n32_controlled_dma_64 U] [$b getName]]
set f [open /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/$kind-outputs.txt]
set n 0
set selected_ports {}
set driverlog [open $out/final-drivers.tsv w]
while {[gets $f p] >= 0} {
 set p [string trim $p];if {$p eq ""} {continue}
 set port [$b findBTerm $p]
 set drivers {}
 foreach it [[$port getNet] getITerms] {
  if {[[$it getMTerm] getIoType] eq "OUTPUT"} {lappend drivers [[$it getInst] getMaster]}
 }
 if {[llength $drivers]!=1} {error "Driver cardinality changed $p"}
 set name [[lindex $drivers 0] getName]
 if {![string match *-baseline-* $res] && (![regexp {^(BUF|INV|CLKBUF)_X([0-9]+)$} $name -> family strength] || $strength<8)} {error "Output strength failed $p $name"}
 puts $driverlog "$p\t$name"
 lappend selected_ports $p
 incr n
}
close $f
close $driverlog
if {$n!=153} {error "Output count changed"}
check_placement -verbose
sta::find_timing
set f [open $out/counts.tsv w]
puts $f "setup\t[sta::endpoint_violation_count max]"
puts $f "hold\t[sta::endpoint_violation_count min]"
foreach kind {capacitance slew fanout} {puts $f "$kind\t[sta::max_${kind}_violation_count]"}
close $f
write_sdc -digits 9 $out/readback.sdc
report_worst_slack -max -digits 6 > $out/setup.rpt
report_worst_slack -min -digits 6 > $out/hold.rpt
report_checks -path_delay min_max -group_path_count 30 -digits 6 > $out/paths.rpt
report_check_types -max_slew -max_capacitance -max_fanout -violators -digits 6 > $out/electrical.rpt
check_setup -verbose > $out/constraints.rpt
report_check_types -recovery -removal -violators -verbose -digits 6 > $out/async-violations.rpt
report_checks -from [get_ports rst_ni] -path_delay min_max -format full_clock_expanded -group_path_count 30 -digits 6 > $out/reset-paths.rpt
check_antennas -report_file $out/antenna.rpt
drt::check_drc_cmd $out/openroad-drc.rpt 0 0 0 0 issue289
foreach net {VDD VSS} {
 if {[check_power_grid -net $net] ne "1"} {error "Incomplete power grid $net"}
}
foreach load {500 1000} {
 set_load $load [get_ports $selected_ports]
 sta::find_timing
 report_worst_slack -max -digits 6 > $out/load-${load}fF-setup.rpt
 report_worst_slack -min -digits 6 > $out/load-${load}fF-hold.rpt
 report_check_types -max_slew -max_capacitance -max_fanout -violators -digits 6 > $out/load-${load}fF-electrical.rpt
 report_checks -to [get_ports $selected_ports] -path_delay min_max -group_path_count 20 -digits 6 > $out/load-${load}fF-output-paths.rpt
}
set_load 50 [get_ports $selected_ports]
puts SIGNOFF_REPORTS_CREATED_NOT_YET_ACCEPTED
