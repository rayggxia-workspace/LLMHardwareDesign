# Independent post-route STA: exact original SDC and actual extracted SPEF.
set_thread_count $::env(OMP_NUM_THREADS)
read_liberty /OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib
read_db $::env(DM_ODB)
read_sdc $::env(DM_SDC)
read_spef $::env(DM_SPEF)
set_propagated_clock [all_clocks]
sta::find_timing
report_units
write_sdc constraints-readback.sdc
check_setup -verbose > coverage.rpt
report_parasitic_annotation -report_unannotated > annotation.rpt
set a [open annotation.rpt r]
set annotations [read $a]
close $a
set a [open annotation-connectivity.tsv w]
set phase before
set names {}
foreach line [split $annotations \n] {
 set name [string trim $line]
 if {$name eq ""} {continue}
 if {[regexp {^Found ([0-9]+) unannotated drivers\.$} $name -> count]} {
  if {$phase ne "before"} {error "Malformed annotation header"}
  set phase drivers
 } elseif {[regexp {^Found ([0-9]+) partially unannotated drivers\.$} $name -> partial]} {
  if {$phase ne "drivers"} {error "Malformed annotation footer"}
  set phase done
 } else {
  if {$phase ne "drivers"} {error "Malformed annotation driver"}
  lappend names $name
 }
}
if {$phase ne "done" || [llength $names]!=$count || $partial!=0} {error "Incomplete parasitic annotation"}
foreach name $names {
 set pins [get_pins -quiet $name]
 if {![llength $pins]} {set pins [get_ports -quiet $name]}
 if {[llength $pins]!=1} {error "Unresolved annotation driver"}
 set fanout 0
 foreach p [get_fanout -from $pins -flat -pin_levels 2 -trace_arcs all] {
  if {[lsearch -exact $pins $p]<0} {incr fanout}
 }
 puts $a "$name\t$fanout"
}
close $a
report_worst_slack -max -digits 9 > timing.rpt
report_worst_slack -min -digits 9 >> timing.rpt
report_tns -max -digits 9 >> timing.rpt
report_tns -min -digits 9 >> timing.rpt
report_checks -path_delay min_max -group_path_count 10 -digits 9 -format full_clock_expanded >> timing.rpt
report_check_types -max_capacitance -max_slew -max_fanout -violators -digits 9 -no_line_splits > electrical.rpt
report_check_types -recovery -removal -min_pulse_width -min_period -violators -digits 9 -no_line_splits > clock-reset.rpt
set f [open summary.tsv w]
puts $f "setup_violations\t[sta::endpoint_violation_count max]"
puts $f "hold_violations\t[sta::endpoint_violation_count min]"
puts $f "time_unit_seconds\t[sta::time_ui_sta 1]"
puts $f "capacitance_unit_farads\t[sta::capacitance_ui_sta 1]"
foreach clock [all_clocks] {
 puts $f "clock\t[get_full_name $clock]\t[get_property $clock period]\t[get_property $clock is_propagated]"
}
foreach kind {capacitance slew fanout} {
 puts $f "$kind\t[sta::max_${kind}_violation_count]\t[sta::max_${kind}_check_slack]\t[sta::max_${kind}_check_limit]"
}
close $f
set f [open paths.tsv w]
foreach a {core mem} {
 foreach b {core mem} {
  foreach kind {max min} {
   set paths [find_timing_paths -from [get_clocks $a] -to [get_clocks $b] -path_delay $kind -group_path_count 1 -sort_by_slack]
   foreach p $paths {
    puts $f "$a\t$b\t$kind\t[get_property $p slack]\t[get_full_name [get_property $p startpoint]]\t[get_full_name [get_property $p endpoint]]"
   }
   report_checks -from [get_clocks $a] -to [get_clocks $b] -path_delay $kind -group_path_count 3 -digits 9 -format full_clock_expanded > $a-$b-$kind.rpt
  }
 }
}
close $f
set f [open endpoints.tsv w]
foreach p [sta::endpoints] {
 puts $f "[get_full_name $p]\t[get_property $p slack_max]\t[get_property $p slack_min]\t[get_property $p is_port]\t[get_property $p direction]"
}
close $f
# Physical net connectivity and constants; no timing endpoint waiver by name alone.
set block [ord::get_db_block]
set f [open connectivity.tsv w]
foreach inst [$block getInsts] {
 set master [[$inst getMaster] getName]
 foreach term [$inst getITerms] {
  set mt [$term getMTerm]
  if {[$mt getSigType] in {POWER GROUND}} {continue}
  set name "[$inst getName]/[$mt getName]"
  set net [$term getNet]
  if {$net eq "NULL"} {
   puts $f "$name\t$master\t[$mt getIoType]\tOPEN\t\t"
  } else {
   set ties {};set drivers 0;set loads 0
   foreach pin [$net getITerms] {
    set dir [[$pin getMTerm] getIoType]
    if {$dir eq "OUTPUT"} {
     incr drivers
     set m [[[$pin getInst] getMaster] getName]
     if {$m in {LOGIC0_X1 LOGIC1_X1}} {lappend ties $m}
    }
    if {$dir eq "INPUT"} {incr loads}
   }
   foreach pin [$net getBTerms] {
    if {[$pin getIoType] eq "INPUT"} {incr drivers}
    if {[$pin getIoType] eq "OUTPUT"} {incr loads}
   }
   puts $f "$name\t$master\t[$mt getIoType]\t[$net getName]\t[join $ties ,]\t$drivers\t$loads\t[$inst getPlacementStatus]"
  }
 }
}
close $f
source $::env(DM_PAIRS)
exit
