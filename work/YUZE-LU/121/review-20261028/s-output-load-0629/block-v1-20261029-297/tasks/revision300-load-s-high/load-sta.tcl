set ::env(BV1_ODB) {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/block-v1-20261029-280/tasks/revision300-final-source-s/flow/results/nangate45/bv1_block_v1_s16k/base/6_final.odb}
set ::env(BV1_SDC) {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/block-v1-20261029-280/tasks/revision300-final-source-s/flow/results/nangate45/bv1_block_v1_s16k/base/6_final.sdc}
set ::env(BV1_SPEF) {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/block-v1-20261029-280/tasks/revision300-final-source-s/flow/results/nangate45/bv1_block_v1_s16k/base/6_final.spef}
rename write_sdc bv1_original_write_sdc
proc write_sdc {args} {uplevel 1 [list bv1_original_write_sdc -digits 12 {*}$args]}
# Read-only independent STA. A fresh process reads actual ODB/SDC/SPEF.
set platform /OpenROAD-flow-scripts/flow/platforms/nangate45
set_thread_count $::env(OMP_NUM_THREADS)
read_liberty $platform/lib/NangateOpenCellLibrary_typical.lib
read_db $::env(BV1_ODB)
read_sdc $::env(BV1_SDC)
set_load 134.393128689673 [get_ports {dout[0]}]
set_load 134.393128689673 [get_ports {dout[100]}]
set_load 134.393128689673 [get_ports {dout[101]}]
set_load 134.393128689673 [get_ports {dout[102]}]
set_load 134.393128689673 [get_ports {dout[103]}]
set_load 134.393128689673 [get_ports {dout[104]}]
set_load 134.393128689673 [get_ports {dout[105]}]
set_load 134.393128689673 [get_ports {dout[106]}]
set_load 134.393128689673 [get_ports {dout[107]}]
set_load 134.393128689673 [get_ports {dout[108]}]
set_load 134.393128689673 [get_ports {dout[109]}]
set_load 134.393128689673 [get_ports {dout[10]}]
set_load 134.393128689673 [get_ports {dout[110]}]
set_load 134.393128689673 [get_ports {dout[111]}]
set_load 136.257820643049 [get_ports {dout[112]}]
set_load 136.257820643049 [get_ports {dout[113]}]
set_load 136.257820643049 [get_ports {dout[114]}]
set_load 136.257820643049 [get_ports {dout[115]}]
set_load 136.257820643049 [get_ports {dout[116]}]
set_load 136.257820643049 [get_ports {dout[117]}]
set_load 136.257820643049 [get_ports {dout[118]}]
set_load 136.257820643049 [get_ports {dout[119]}]
set_load 134.393128689673 [get_ports {dout[11]}]
set_load 136.257820643049 [get_ports {dout[120]}]
set_load 136.257820643049 [get_ports {dout[121]}]
set_load 136.257820643049 [get_ports {dout[122]}]
set_load 136.257820643049 [get_ports {dout[123]}]
set_load 136.257820643049 [get_ports {dout[124]}]
set_load 136.257820643049 [get_ports {dout[125]}]
set_load 136.257820643049 [get_ports {dout[126]}]
set_load 136.257820643049 [get_ports {dout[127]}]
set_load 134.393128689673 [get_ports {dout[12]}]
set_load 134.393128689673 [get_ports {dout[13]}]
set_load 134.393128689673 [get_ports {dout[14]}]
set_load 134.393128689673 [get_ports {dout[15]}]
set_load 136.257820643049 [get_ports {dout[16]}]
set_load 136.257820643049 [get_ports {dout[17]}]
set_load 136.257820643049 [get_ports {dout[18]}]
set_load 136.257820643049 [get_ports {dout[19]}]
set_load 134.393128689673 [get_ports {dout[1]}]
set_load 136.257820643049 [get_ports {dout[20]}]
set_load 136.257820643049 [get_ports {dout[21]}]
set_load 136.257820643049 [get_ports {dout[22]}]
set_load 136.257820643049 [get_ports {dout[23]}]
set_load 136.257820643049 [get_ports {dout[24]}]
set_load 136.257820643049 [get_ports {dout[25]}]
set_load 136.257820643049 [get_ports {dout[26]}]
set_load 136.257820643049 [get_ports {dout[27]}]
set_load 136.257820643049 [get_ports {dout[28]}]
set_load 136.257820643049 [get_ports {dout[29]}]
set_load 134.393128689673 [get_ports {dout[2]}]
set_load 136.257820643049 [get_ports {dout[30]}]
set_load 136.257820643049 [get_ports {dout[31]}]
set_load 134.393128689673 [get_ports {dout[32]}]
set_load 134.393128689673 [get_ports {dout[33]}]
set_load 134.393128689673 [get_ports {dout[34]}]
set_load 134.393128689673 [get_ports {dout[35]}]
set_load 134.393128689673 [get_ports {dout[36]}]
set_load 134.393128689673 [get_ports {dout[37]}]
set_load 134.393128689673 [get_ports {dout[38]}]
set_load 134.393128689673 [get_ports {dout[39]}]
set_load 134.393128689673 [get_ports {dout[3]}]
set_load 134.393128689673 [get_ports {dout[40]}]
set_load 134.393128689673 [get_ports {dout[41]}]
set_load 134.393128689673 [get_ports {dout[42]}]
set_load 134.393128689673 [get_ports {dout[43]}]
set_load 134.393128689673 [get_ports {dout[44]}]
set_load 134.393128689673 [get_ports {dout[45]}]
set_load 134.393128689673 [get_ports {dout[46]}]
set_load 134.393128689673 [get_ports {dout[47]}]
set_load 136.257820643049 [get_ports {dout[48]}]
set_load 136.257820643049 [get_ports {dout[49]}]
set_load 134.393128689673 [get_ports {dout[4]}]
set_load 136.257820643049 [get_ports {dout[50]}]
set_load 136.257820643049 [get_ports {dout[51]}]
set_load 136.257820643049 [get_ports {dout[52]}]
set_load 136.257820643049 [get_ports {dout[53]}]
set_load 136.257820643049 [get_ports {dout[54]}]
set_load 136.257820643049 [get_ports {dout[55]}]
set_load 136.257820643049 [get_ports {dout[56]}]
set_load 136.257820643049 [get_ports {dout[57]}]
set_load 136.257820643049 [get_ports {dout[58]}]
set_load 136.257820643049 [get_ports {dout[59]}]
set_load 134.393128689673 [get_ports {dout[5]}]
set_load 136.257820643049 [get_ports {dout[60]}]
set_load 136.257820643049 [get_ports {dout[61]}]
set_load 136.257820643049 [get_ports {dout[62]}]
set_load 136.257820643049 [get_ports {dout[63]}]
set_load 134.393128689673 [get_ports {dout[64]}]
set_load 134.393128689673 [get_ports {dout[65]}]
set_load 134.393128689673 [get_ports {dout[66]}]
set_load 134.393128689673 [get_ports {dout[67]}]
set_load 134.393128689673 [get_ports {dout[68]}]
set_load 134.393128689673 [get_ports {dout[69]}]
set_load 134.393128689673 [get_ports {dout[6]}]
set_load 134.393128689673 [get_ports {dout[70]}]
set_load 134.393128689673 [get_ports {dout[71]}]
set_load 134.393128689673 [get_ports {dout[72]}]
set_load 134.393128689673 [get_ports {dout[73]}]
set_load 134.393128689673 [get_ports {dout[74]}]
set_load 134.393128689673 [get_ports {dout[75]}]
set_load 134.393128689673 [get_ports {dout[76]}]
set_load 134.393128689673 [get_ports {dout[77]}]
set_load 134.393128689673 [get_ports {dout[78]}]
set_load 134.393128689673 [get_ports {dout[79]}]
set_load 134.393128689673 [get_ports {dout[7]}]
set_load 136.257820643049 [get_ports {dout[80]}]
set_load 136.257820643049 [get_ports {dout[81]}]
set_load 136.257820643049 [get_ports {dout[82]}]
set_load 136.257820643049 [get_ports {dout[83]}]
set_load 136.257820643049 [get_ports {dout[84]}]
set_load 136.257820643049 [get_ports {dout[85]}]
set_load 136.257820643049 [get_ports {dout[86]}]
set_load 136.257820643049 [get_ports {dout[87]}]
set_load 136.257820643049 [get_ports {dout[88]}]
set_load 136.257820643049 [get_ports {dout[89]}]
set_load 134.393128689673 [get_ports {dout[8]}]
set_load 136.257820643049 [get_ports {dout[90]}]
set_load 136.257820643049 [get_ports {dout[91]}]
set_load 136.257820643049 [get_ports {dout[92]}]
set_load 136.257820643049 [get_ports {dout[93]}]
set_load 136.257820643049 [get_ports {dout[94]}]
set_load 136.257820643049 [get_ports {dout[95]}]
set_load 134.393128689673 [get_ports {dout[96]}]
set_load 134.393128689673 [get_ports {dout[97]}]
set_load 134.393128689673 [get_ports {dout[98]}]
set_load 134.393128689673 [get_ports {dout[99]}]
set_load 134.393128689673 [get_ports {dout[9]}]
set_load 134.393128689673 [get_ports {ready}]
set_load 136.257820643049 [get_ports {valid}]
report_units
read_spef $::env(BV1_SPEF)
set_propagated_clock [all_clocks]
sta::find_timing
set clock_fanout 0
set clock_ports [get_ports clk]
foreach reached [get_fanout -from $clock_ports -flat -pin_levels 2 -trace_arcs all] {
  if {[lsearch -exact $clock_ports $reached]<0} {incr clock_fanout}
}
if {$clock_fanout==0} {error "Native fanout API failed its connected-clock positive control"}
write_sdc constraints-readback.sdc
report_parasitic_annotation -report_unannotated > annotation.rpt
source {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/block-v1-20261029-297/src/project/experiments/block_v1/native_annotation.tcl}
set stream [open endpoints.tsv w]
foreach pin [sta::endpoints] {
  set maximum [get_property $pin slack_max]
  set minimum [get_property $pin slack_min]
  set unused_fanout -1
  if {$maximum in {INF -INF} && $minimum in {INF -INF}} {
    set unused_fanout 0
    foreach reached [get_fanout -from [list $pin] -flat -pin_levels 2 -trace_arcs all] {
      if {$reached ne $pin} {incr unused_fanout}
    }
  }
  puts $stream "[get_full_name $pin]\t$maximum\t$minimum\t[get_property $pin is_port]\t[string tolower [get_property $pin direction]]\t$unused_fanout"
}
close $stream
set stream [open timing-summary.tsv w]
puts $stream "setup_checks\t[sta::endpoint_violation_count max]"
puts $stream "hold_checks\t[sta::endpoint_violation_count min]"
puts $stream "connected_clock_fanout\t$clock_fanout"
puts $stream "check_setup\t[check_setup -verbose]"
puts $stream "time_unit_seconds\t[sta::time_ui_sta 1]"
puts $stream "capacitance_unit_farads\t[sta::capacitance_ui_sta 1]"
foreach clock [all_clocks] {
  puts $stream "clock\t[get_full_name $clock]\t[get_property $clock is_propagated]"
}
foreach kind {capacitance slew fanout} {
  puts $stream "$kind\t[sta::max_${kind}_violation_count]\t[sta::max_${kind}_check_slack]\t[sta::max_${kind}_check_limit]"
}
close $stream
report_worst_slack -max -digits 9 > timing.rpt
report_worst_slack -min -digits 9 >> timing.rpt
report_tns -max -digits 9 >> timing.rpt
report_tns -min -digits 9 >> timing.rpt
report_checks -path_delay min_max -group_path_count 10 -digits 9 -format full_clock_expanded >> timing.rpt
# Delay checks are covered by the complete endpoint table and native counts.
report_check_types -max_capacitance -max_slew -max_fanout -violators -digits 9 -no_line_splits > electrical-violations.rpt
report_check_types -max_capacitance -max_slew -max_fanout -max_count 3 -digits 9 -no_line_splits > electrical-worst.rpt
