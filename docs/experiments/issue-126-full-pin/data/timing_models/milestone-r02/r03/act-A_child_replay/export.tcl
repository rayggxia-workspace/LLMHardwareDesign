read_liberty {/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib}
read_liberty {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-7/parallel-blocks-wave2-06/act-cap20/memory-model/macros/fakeram45_1r1w_32x64.lib}
read_liberty {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-7/parallel-blocks-wave2-06/act-cap20/memory-model/macros/fakeram45_1r1w_32x128.lib}
read_db {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/finalized/fullC-r01/act-A_replay/clean.odb}
read_sdc {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-7/parallel-blocks-wave2-06/act-cap20/flow/results/nangate45/parallel_opentpu_act/base/6_final.sdc}
source /OpenROAD-flow-scripts/flow/platforms/nangate45/setRC.tcl
read_spef {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/trials/fullC-r01/act-A_replay/extracted.spef}
report_worst_slack -max -digits 6 > {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/leaf_timing_models/r03/act-A_child_replay/setup.txt}
report_worst_slack -min -digits 6 > {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/leaf_timing_models/r03/act-A_child_replay/hold.txt}
report_parasitic_annotation -report_unannotated > {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/leaf_timing_models/r03/act-A_child_replay/parasitic_coverage.txt}
check_setup -verbose > {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/leaf_timing_models/r03/act-A_child_replay/constraint_coverage.txt}
report_check_types -violators -max_delay -min_delay -max_slew -max_capacitance -max_fanout -recovery -removal -max_count 1000000 -digits 6 > {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/leaf_timing_models/r03/act-A_child_replay/checks.txt}
write_timing_model {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/leaf_timing_models/r03/act-A_child_replay/timing.lib}
set f [open {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/leaf_timing_models/r03/act-A_child_replay/native_library_sha256.txt} w]
puts $f [exec sha256sum {/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib}]
puts $f [exec sha256sum {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-7/parallel-blocks-wave2-06/act-cap20/memory-model/macros/fakeram45_1r1w_32x64.lib}]
puts $f [exec sha256sum {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-7/parallel-blocks-wave2-06/act-cap20/memory-model/macros/fakeram45_1r1w_32x128.lib}]
puts $f [exec sha256sum /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad]
close $f
