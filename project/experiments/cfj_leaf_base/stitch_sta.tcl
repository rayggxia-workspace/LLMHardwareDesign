# Timing sensitivity on the linked circuit with extracted native plus modeled upper RC.
set run $::env(CFJ_OVERLAY_DIR)
set variant $::env(CFJ_UPPER_RC_VARIANT)
set top $::env(CFJ_FINAL_TOP)
read_liberty /OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib
foreach liberty [split $::env(CFJ_FINAL_LIBS)] {read_liberty $liberty}
set tech /OpenROAD-flow-scripts/flow/platforms/nangate45/lef
read_lef $tech/NangateOpenCellLibrary.tech.lef
read_lef $tech/NangateOpenCellLibrary.macro.mod.lef
foreach lef [split $::env(CFJ_FINAL_LEFS)] {read_lef $lef}
read_verilog $run/stitched.v
link_design $top
read_sdc $run/input.sdc
read_spef $run/stitched-$variant.spef
set_propagated_clock [all_clocks]
report_parasitic_annotation -report_unannotated > $run/stitched-$variant-annotation.rpt
report_checks -path_delay min_max -group_path_count 20 > $run/stitched-$variant-paths.rpt
report_worst_slack -max -digits 6 > $run/stitched-$variant-summary.rpt
report_worst_slack -min -digits 6 >> $run/stitched-$variant-summary.rpt
report_check_types -max_slew -max_capacitance -max_fanout -violators -digits 6 >> $run/stitched-$variant-summary.rpt
