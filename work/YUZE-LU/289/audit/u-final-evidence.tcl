read_liberty /OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib
foreach lib $::env(U_LIBS) {read_liberty $lib}
read_db $::env(U_FINAL_RES)/6_final.odb
read_sdc $::env(U_FINAL_RES)/6_final.sdc
read_spef $::env(U_FINAL_RES)/6_final.spef
set_propagated_clock [all_clocks]
sta::find_timing
set o [open counts.tsv w]
puts $o "setup\t[sta::endpoint_violation_count max]"
puts $o "hold\t[sta::endpoint_violation_count min]"
foreach kind {capacitance slew fanout} {puts $o "$kind\t[sta::max_${kind}_violation_count]"}
close $o
report_worst_slack -max -digits 9 > setup.rpt
report_worst_slack -min -digits 9 > hold.rpt
report_check_types -max_slew -max_capacitance -max_fanout -violators -digits 9 > electrical.rpt
report_check_types -recovery -removal -violators -verbose -digits 9 > async.rpt
source /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/geometry.tcl
geometry_snapshot final-geometry.tsv
set block [ord::get_db_block]
set f [open /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/U-outputs.txt]
set o [open drivers.tsv w]
set n 0
while {[gets $f name]>=0} {
 if {$name eq ""} {continue}
 set bt [$block findBTerm $name]
 if {$bt eq "NULL" || [$bt getIoType] ne "OUTPUT"} {error "Missing output $name"}
 set net [$bt getNet];set drivers {}
 foreach it [$net getITerms] {if {[[$it getMTerm] getIoType] eq "OUTPUT"} {lappend drivers $it}}
 if {[llength $drivers]!=1} {error "Driver cardinality $name"}
 set it [lindex $drivers 0];set i [$it getInst];set master [[$i getMaster] getName]
 if {![regexp {^(BUF|INV|CLKBUF)_X([0-9]+)$} $master -> family strength] || $strength<8} {error "Non-X8 $name $master"}
 puts $o "$name\t[$net getName]\t[$i getName]\t$master\t[[$it getMTerm] getName]"
 incr n
}
close $o;close $f
if {$n!=153} {error "Output count mismatch"}
set o [open pg.tsv w]
foreach rail {VDD VSS} {
 set value [check_power_grid -net $rail]
 puts $o "$rail\t$value"
 if {$value ne "1"} {error "PG failed $rail"}
}
close $o
puts INDEPENDENT_DRIVER_PG_PASS
