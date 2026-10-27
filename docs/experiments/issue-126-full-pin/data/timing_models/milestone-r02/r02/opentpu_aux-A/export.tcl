read_liberty {/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib}
read_liberty {/public/home/yuzelu/project-circuit/llm_routing_analysis/repos/openTPU/build/asic/small/macros/fakeram45_1r1w_1024x128.lib}
read_liberty {/public/home/yuzelu/project-circuit/llm_routing_analysis/repos/openTPU/build/asic/small/macros/fakeram45_1r1w_128x128.lib}
read_liberty {/public/home/yuzelu/project-circuit/llm_routing_analysis/repos/openTPU/build/asic/small/macros/fakeram45_1r1w_4096x32.lib}
read_liberty {/public/home/yuzelu/project-circuit/llm_routing_analysis/repos/openTPU/build/asic/small/macros/fakeram45_1r1w_512x31.lib}
read_db {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/finalized/r03/opentpu_aux-A/clean.odb}
read_sdc {/public/home/yuzelu/PingyangHuang/issue-55/full-block-integration-20261023T103718349596Z/runs/auxiliary-route-opentpu-4c-01/flow/results/nangate45/hpy_opentpu_aux/base/5_1_grt.sdc}
source /OpenROAD-flow-scripts/flow/platforms/nangate45/setRC.tcl
read_spef {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/trials/r03/opentpu_aux-A/extracted.spef}
report_worst_slack -max -digits 6 > {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/leaf_timing_models/r02/opentpu_aux-A/setup.txt}
report_worst_slack -min -digits 6 > {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/leaf_timing_models/r02/opentpu_aux-A/hold.txt}
report_parasitic_annotation -report_unannotated > {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/leaf_timing_models/r02/opentpu_aux-A/parasitic_coverage.txt}
check_setup -verbose > {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/leaf_timing_models/r02/opentpu_aux-A/constraint_coverage.txt}
report_check_types -violators -max_delay -min_delay -max_slew -max_capacitance -max_fanout -recovery -removal -max_count 1000000 -digits 6 > {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/leaf_timing_models/r02/opentpu_aux-A/checks.txt}
write_timing_model {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/leaf_timing_models/r02/opentpu_aux-A/timing.lib}
set f [open {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/leaf_timing_models/r02/opentpu_aux-A/native_library_sha256.txt} w]
puts $f [exec sha256sum {/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib}]
puts $f [exec sha256sum {/public/home/yuzelu/project-circuit/llm_routing_analysis/repos/openTPU/build/asic/small/macros/fakeram45_1r1w_1024x128.lib}]
puts $f [exec sha256sum {/public/home/yuzelu/project-circuit/llm_routing_analysis/repos/openTPU/build/asic/small/macros/fakeram45_1r1w_128x128.lib}]
puts $f [exec sha256sum {/public/home/yuzelu/project-circuit/llm_routing_analysis/repos/openTPU/build/asic/small/macros/fakeram45_1r1w_4096x32.lib}]
puts $f [exec sha256sum {/public/home/yuzelu/project-circuit/llm_routing_analysis/repos/openTPU/build/asic/small/macros/fakeram45_1r1w_512x31.lib}]
puts $f [exec sha256sum /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad]
close $f
