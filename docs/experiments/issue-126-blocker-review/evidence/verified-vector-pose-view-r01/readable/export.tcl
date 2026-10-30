read_liberty {/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib}
read_db {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/vector_pose_fixed_views/r01/vector-C/clean.odb}
write_abstract_lef {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/vector_pose_fixed_views/r01/vector-C/abstract.lef}
write_abstract_lef -bloat_factor 0 {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/vector_pose_fixed_views/r01/vector-C/detailed.lef}
write_def {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/vector_pose_fixed_views/r01/vector-C/clean.def}
write_verilog {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/vector_pose_fixed_views/r01/vector-C/clean.v}
set b [ord::get_db_block];set f [open {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/vector_pose_fixed_views/r01/vector-C/pins.tsv} w];puts $f "pin\tdirection\tuse\tnet\tlayer\tx0\ty0\tx1\ty1";foreach p [$b getBTerms] {foreach bp [$p getBPins] {foreach r [$bp getBoxes] {puts $f [join [list [$p getName] [$p getIoType] [$p getSigType] [[$p getNet] getName] [[$r getTechLayer] getName] [$r xMin] [$r yMin] [$r xMax] [$r yMax]] "\t"]}}};close $f
read_sdc {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-7/vec-physical-01/flow/results/nangate45/llhd_vec_original/base/6_final.sdc}
source /OpenROAD-flow-scripts/flow/platforms/nangate45/setRC.tcl
read_spef {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/vector_pose_route_fix/r01/extracted.spef}
report_worst_slack -max -digits 6 > {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/vector_pose_fixed_views/r01/vector-C/setup.txt}
report_worst_slack -min -digits 6 > {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/vector_pose_fixed_views/r01/vector-C/hold.txt}
report_parasitic_annotation -report_unannotated > {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/vector_pose_fixed_views/r01/vector-C/parasitic_coverage.txt}
check_setup -verbose > {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/vector_pose_fixed_views/r01/vector-C/constraint_coverage.txt}
write_timing_model {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/vector_pose_fixed_views/r01/vector-C/timing.lib}
