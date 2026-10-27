read_liberty {/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib}
read_db {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/finalized/r01/gemm-A/clean.odb}
read_sdc {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-7/parallel-blocks-wave2-06/gemm-cap20/flow/results/nangate45/parallel_llaccel_gemm/base/6_final.sdc}
source /OpenROAD-flow-scripts/flow/platforms/nangate45/setRC.tcl
read_spef {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/trials/r01/gemm-A/extracted.spef}
report_worst_slack -max -digits 6 > {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/leaf_timing_models/r02/gemm-A/setup.txt}
report_worst_slack -min -digits 6 > {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/leaf_timing_models/r02/gemm-A/hold.txt}
report_parasitic_annotation -report_unannotated > {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/leaf_timing_models/r02/gemm-A/parasitic_coverage.txt}
check_setup -verbose > {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/leaf_timing_models/r02/gemm-A/constraint_coverage.txt}
report_check_types -violators -max_delay -min_delay -max_slew -max_capacitance -max_fanout -recovery -removal -max_count 1000000 -digits 6 > {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/leaf_timing_models/r02/gemm-A/checks.txt}
write_timing_model {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/leaf_timing_models/r02/gemm-A/timing.lib}
set f [open {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/leaf_timing_models/r02/gemm-A/native_library_sha256.txt} w]
puts $f [exec sha256sum {/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib}]
puts $f [exec sha256sum /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad]
close $f
