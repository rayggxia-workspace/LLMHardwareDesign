set_thread_count 16
read_liberty {/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib}
read_lef {/OpenROAD-flow-scripts/flow/platforms/nangate45/lef/NangateOpenCellLibrary.tech.lef}
read_lef {/OpenROAD-flow-scripts/flow/platforms/nangate45/lef/NangateOpenCellLibrary.macro.mod.lef}
read_verilog {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/endpoint-gates-01/function/physical-functional.v}
read_verilog {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/d-gates-07/function/physical-functional.v}
read_verilog {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/c-gates-01/function/physical-functional.v}
read_verilog {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/adapter-gates-01/adapter_s/function/physical-functional.v}
read_verilog {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/adapter-gates-01/adapter_m/function/physical-functional.v}
read_verilog {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/e-gates-04/function/physical-functional.v}
read_verilog {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/adapter-gates-02/adapter_t/function/physical-functional.v}
read_verilog {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/adapter-gates-02/adapter_n/function/physical-functional.v}
read_verilog {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/adapter-gates-02/axil/function/physical-functional.v}
read_verilog {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/adapter-gates-02/adapter_g/function/physical-functional.v}
read_verilog {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/fabric-gates-01/route/function/physical-functional.v}
read_verilog {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/fabric-gates-01/s_arbiter/function/physical-functional.v}
read_verilog {/public/home/yuzelu/project-circuit/llm_routing_analysis/worktrees/issue143-seven-block-v2-20261030/outputs/018/function-m/physical-functional.v}
read_verilog {/public/home/yuzelu/project-circuit/llm_routing_analysis/worktrees/issue143-seven-block-v2-20261030/outputs/028/function-n/physical-functional.v}
read_verilog {/public/home/yuzelu/project-circuit/llm_routing_analysis/worktrees/issue143-seven-block-v2-20261030/outputs/066/function-e/physical-functional.v}
read_verilog {/public/home/yuzelu/project-circuit/llm_routing_analysis/worktrees/issue143-seven-block-v2-20261030/outputs/010/function-g/physical-functional.v}
read_verilog {/public/home/yuzelu/project-circuit/llm_routing_analysis/worktrees/issue130-m-feed-qualify43-20261030/results/function-s/physical-functional.v}
read_verilog {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/block-v1-20261028-249/tasks/revision300-final-function-t/physical-functional.v}
read_verilog {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/status-gates-01/function/physical-functional.v}
read_verilog {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/system-sta-ideal-02/combined.v}
link_design -hier control_system
read_sdc {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/system-sta-ideal-02/combined.sdc}
read_spef -path {controller} {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/c-gates-01/deliver/6_final.spef}
read_spef -path {endpoint_0} {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/d-gates-07/deliver/6_final.spef}
read_spef -path {endpoint_1} {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/adapter-gates-01/adapter_m/deliver/6_final.spef}
read_spef -path {endpoint_2} {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/adapter-gates-02/adapter_n/deliver/6_final.spef}
read_spef -path {endpoint_3} {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/e-gates-04/deliver/6_final.spef}
read_spef -path {endpoint_4} {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/adapter-gates-02/adapter_g/deliver/6_final.spef}
read_spef -path {endpoint_5} {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/adapter-gates-01/adapter_s/deliver/6_final.spef}
read_spef -path {endpoint_6} {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/adapter-gates-02/adapter_t/deliver/6_final.spef}
read_spef -path {host} {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/adapter-gates-02/axil/deliver/6_final.spef}
read_spef -path {macro_1} {/public/home/yuzelu/project-circuit/llm_routing_analysis/worktrees/issue143-seven-block-v2-20261030/outputs/018/deliver-m/6_final.spef}
read_spef -path {macro_2} {/public/home/yuzelu/project-circuit/llm_routing_analysis/worktrees/issue143-seven-block-v2-20261030/outputs/028/deliver-n/6_final.spef}
read_spef -path {macro_3} {/public/home/yuzelu/project-circuit/llm_routing_analysis/worktrees/issue143-seven-block-v2-20261030/outputs/066/deliver-e/6_final.spef}
read_spef -path {macro_4} {/public/home/yuzelu/project-circuit/llm_routing_analysis/worktrees/issue143-seven-block-v2-20261030/outputs/010/deliver-g/6_final.spef}
read_spef -path {macro_s} {/public/home/yuzelu/project-circuit/llm_routing_analysis/worktrees/issue130-m-feed-qualify43-20261030/results/delivery-s/native/6_final.spef}
read_spef -path {macro_t} {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/block-v1-20261028-249/tasks/revision300-final-source-t/flow/results/nangate45/bv1_transaction6k/base/6_final.spef}
read_spef -path {queue_0} {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/endpoint-drc-02/deliver/6_final.spef}
read_spef -path {queue_1} {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/endpoint-drc-02/deliver/6_final.spef}
read_spef -path {queue_2} {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/endpoint-drc-02/deliver/6_final.spef}
read_spef -path {queue_3} {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/endpoint-drc-02/deliver/6_final.spef}
read_spef -path {queue_4} {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/endpoint-drc-02/deliver/6_final.spef}
read_spef -path {queue_5} {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/endpoint-drc-02/deliver/6_final.spef}
read_spef -path {queue_6} {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/endpoint-drc-02/deliver/6_final.spef}
read_spef -path {routes} {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/fabric-gates-01/route/deliver/6_final.spef}
read_spef -path {s_port} {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/fabric-gates-01/s_arbiter/deliver/6_final.spef}
read_spef -path {system_status} {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/status-gates-01/deliver/6_final.spef}
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
# Incomplete upper parasitics retained as diagnostic evidence; no acceptance granted.
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
