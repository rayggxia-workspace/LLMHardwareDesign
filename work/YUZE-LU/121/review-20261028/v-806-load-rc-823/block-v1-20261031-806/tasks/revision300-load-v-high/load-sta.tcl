set ::env(BV1_ODB) {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/block-v1-20261031-805/tasks/revision300-final-source-v/flow/results/nangate45/bv1_block_v1_v/base/6_final.odb}
set ::env(BV1_SDC) {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/block-v1-20261031-805/tasks/revision300-final-source-v/flow/results/nangate45/bv1_block_v1_v/base/6_final.sdc}
set ::env(BV1_SPEF) {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/block-v1-20261031-805/tasks/revision300-final-source-v/flow/results/nangate45/bv1_block_v1_v/base/6_final.spef}
rename write_sdc bv1_original_write_sdc
proc write_sdc {args} {uplevel 1 [list bv1_original_write_sdc -digits 12 {*}$args]}
# Read-only independent STA. A fresh process reads actual ODB/SDC/SPEF.
set platform /OpenROAD-flow-scripts/flow/platforms/nangate45
set_thread_count $::env(OMP_NUM_THREADS)
read_liberty $platform/lib/NangateOpenCellLibrary_typical.lib
read_db $::env(BV1_ODB)
read_sdc $::env(BV1_SDC)
set_load 106.422749389038 [get_ports {busy}]
set_load 108.287441342414 [get_ports {cmd_ready}]
set_load 106.422749389038 [get_ports {rsp_data[0]}]
set_load 106.422749389038 [get_ports {rsp_data[100]}]
set_load 106.422749389038 [get_ports {rsp_data[101]}]
set_load 106.422749389038 [get_ports {rsp_data[102]}]
set_load 106.422749389038 [get_ports {rsp_data[103]}]
set_load 106.422749389038 [get_ports {rsp_data[104]}]
set_load 106.422749389038 [get_ports {rsp_data[105]}]
set_load 106.422749389038 [get_ports {rsp_data[106]}]
set_load 106.422749389038 [get_ports {rsp_data[107]}]
set_load 106.422749389038 [get_ports {rsp_data[108]}]
set_load 106.422749389038 [get_ports {rsp_data[109]}]
set_load 106.422749389038 [get_ports {rsp_data[10]}]
set_load 106.422749389038 [get_ports {rsp_data[110]}]
set_load 106.422749389038 [get_ports {rsp_data[111]}]
set_load 108.287441342414 [get_ports {rsp_data[112]}]
set_load 108.287441342414 [get_ports {rsp_data[113]}]
set_load 108.287441342414 [get_ports {rsp_data[114]}]
set_load 108.287441342414 [get_ports {rsp_data[115]}]
set_load 108.287441342414 [get_ports {rsp_data[116]}]
set_load 108.287441342414 [get_ports {rsp_data[117]}]
set_load 108.287441342414 [get_ports {rsp_data[118]}]
set_load 108.287441342414 [get_ports {rsp_data[119]}]
set_load 106.422749389038 [get_ports {rsp_data[11]}]
set_load 108.287441342414 [get_ports {rsp_data[120]}]
set_load 108.287441342414 [get_ports {rsp_data[121]}]
set_load 108.287441342414 [get_ports {rsp_data[122]}]
set_load 108.287441342414 [get_ports {rsp_data[123]}]
set_load 108.287441342414 [get_ports {rsp_data[124]}]
set_load 108.287441342414 [get_ports {rsp_data[125]}]
set_load 108.287441342414 [get_ports {rsp_data[126]}]
set_load 108.287441342414 [get_ports {rsp_data[127]}]
set_load 106.422749389038 [get_ports {rsp_data[12]}]
set_load 106.422749389038 [get_ports {rsp_data[13]}]
set_load 106.422749389038 [get_ports {rsp_data[14]}]
set_load 106.422749389038 [get_ports {rsp_data[15]}]
set_load 108.287441342414 [get_ports {rsp_data[16]}]
set_load 108.287441342414 [get_ports {rsp_data[17]}]
set_load 108.287441342414 [get_ports {rsp_data[18]}]
set_load 108.287441342414 [get_ports {rsp_data[19]}]
set_load 106.422749389038 [get_ports {rsp_data[1]}]
set_load 108.287441342414 [get_ports {rsp_data[20]}]
set_load 108.287441342414 [get_ports {rsp_data[21]}]
set_load 108.287441342414 [get_ports {rsp_data[22]}]
set_load 108.287441342414 [get_ports {rsp_data[23]}]
set_load 108.287441342414 [get_ports {rsp_data[24]}]
set_load 108.287441342414 [get_ports {rsp_data[25]}]
set_load 108.287441342414 [get_ports {rsp_data[26]}]
set_load 108.287441342414 [get_ports {rsp_data[27]}]
set_load 108.287441342414 [get_ports {rsp_data[28]}]
set_load 108.287441342414 [get_ports {rsp_data[29]}]
set_load 106.422749389038 [get_ports {rsp_data[2]}]
set_load 108.287441342414 [get_ports {rsp_data[30]}]
set_load 108.287441342414 [get_ports {rsp_data[31]}]
set_load 106.422749389038 [get_ports {rsp_data[32]}]
set_load 106.422749389038 [get_ports {rsp_data[33]}]
set_load 106.422749389038 [get_ports {rsp_data[34]}]
set_load 106.422749389038 [get_ports {rsp_data[35]}]
set_load 106.422749389038 [get_ports {rsp_data[36]}]
set_load 106.422749389038 [get_ports {rsp_data[37]}]
set_load 106.422749389038 [get_ports {rsp_data[38]}]
set_load 106.422749389038 [get_ports {rsp_data[39]}]
set_load 106.422749389038 [get_ports {rsp_data[3]}]
set_load 106.422749389038 [get_ports {rsp_data[40]}]
set_load 106.422749389038 [get_ports {rsp_data[41]}]
set_load 106.422749389038 [get_ports {rsp_data[42]}]
set_load 106.422749389038 [get_ports {rsp_data[43]}]
set_load 106.422749389038 [get_ports {rsp_data[44]}]
set_load 106.422749389038 [get_ports {rsp_data[45]}]
set_load 106.422749389038 [get_ports {rsp_data[46]}]
set_load 106.422749389038 [get_ports {rsp_data[47]}]
set_load 108.287441342414 [get_ports {rsp_data[48]}]
set_load 108.287441342414 [get_ports {rsp_data[49]}]
set_load 106.422749389038 [get_ports {rsp_data[4]}]
set_load 108.287441342414 [get_ports {rsp_data[50]}]
set_load 108.287441342414 [get_ports {rsp_data[51]}]
set_load 108.287441342414 [get_ports {rsp_data[52]}]
set_load 108.287441342414 [get_ports {rsp_data[53]}]
set_load 108.287441342414 [get_ports {rsp_data[54]}]
set_load 108.287441342414 [get_ports {rsp_data[55]}]
set_load 108.287441342414 [get_ports {rsp_data[56]}]
set_load 108.287441342414 [get_ports {rsp_data[57]}]
set_load 108.287441342414 [get_ports {rsp_data[58]}]
set_load 108.287441342414 [get_ports {rsp_data[59]}]
set_load 106.422749389038 [get_ports {rsp_data[5]}]
set_load 108.287441342414 [get_ports {rsp_data[60]}]
set_load 108.287441342414 [get_ports {rsp_data[61]}]
set_load 108.287441342414 [get_ports {rsp_data[62]}]
set_load 108.287441342414 [get_ports {rsp_data[63]}]
set_load 106.422749389038 [get_ports {rsp_data[64]}]
set_load 106.422749389038 [get_ports {rsp_data[65]}]
set_load 106.422749389038 [get_ports {rsp_data[66]}]
set_load 106.422749389038 [get_ports {rsp_data[67]}]
set_load 106.422749389038 [get_ports {rsp_data[68]}]
set_load 106.422749389038 [get_ports {rsp_data[69]}]
set_load 106.422749389038 [get_ports {rsp_data[6]}]
set_load 106.422749389038 [get_ports {rsp_data[70]}]
set_load 106.422749389038 [get_ports {rsp_data[71]}]
set_load 106.422749389038 [get_ports {rsp_data[72]}]
set_load 106.422749389038 [get_ports {rsp_data[73]}]
set_load 106.422749389038 [get_ports {rsp_data[74]}]
set_load 106.422749389038 [get_ports {rsp_data[75]}]
set_load 106.422749389038 [get_ports {rsp_data[76]}]
set_load 106.422749389038 [get_ports {rsp_data[77]}]
set_load 106.422749389038 [get_ports {rsp_data[78]}]
set_load 106.422749389038 [get_ports {rsp_data[79]}]
set_load 106.422749389038 [get_ports {rsp_data[7]}]
set_load 108.287441342414 [get_ports {rsp_data[80]}]
set_load 108.287441342414 [get_ports {rsp_data[81]}]
set_load 108.287441342414 [get_ports {rsp_data[82]}]
set_load 108.287441342414 [get_ports {rsp_data[83]}]
set_load 108.287441342414 [get_ports {rsp_data[84]}]
set_load 108.287441342414 [get_ports {rsp_data[85]}]
set_load 108.287441342414 [get_ports {rsp_data[86]}]
set_load 108.287441342414 [get_ports {rsp_data[87]}]
set_load 108.287441342414 [get_ports {rsp_data[88]}]
set_load 108.287441342414 [get_ports {rsp_data[89]}]
set_load 106.422749389038 [get_ports {rsp_data[8]}]
set_load 108.287441342414 [get_ports {rsp_data[90]}]
set_load 108.287441342414 [get_ports {rsp_data[91]}]
set_load 108.287441342414 [get_ports {rsp_data[92]}]
set_load 108.287441342414 [get_ports {rsp_data[93]}]
set_load 108.287441342414 [get_ports {rsp_data[94]}]
set_load 108.287441342414 [get_ports {rsp_data[95]}]
set_load 106.422749389038 [get_ports {rsp_data[96]}]
set_load 106.422749389038 [get_ports {rsp_data[97]}]
set_load 106.422749389038 [get_ports {rsp_data[98]}]
set_load 106.422749389038 [get_ports {rsp_data[99]}]
set_load 106.422749389038 [get_ports {rsp_data[9]}]
set_load 106.422749389038 [get_ports {rsp_error}]
set_load 108.287441342414 [get_ports {rsp_saturated}]
set_load 106.422749389038 [get_ports {rsp_valid}]
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
source {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/block-v1-20261031-806/src/project/experiments/block_v1/native_annotation.tcl}
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
