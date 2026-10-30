read_liberty {/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib}
read_db {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/llsys_wire_retention_views/r01/llaccel_aux-C/clean.odb}
write_abstract_lef {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/llsys_wire_retention_views/r01/llaccel_aux-C/abstract.lef}
write_abstract_lef -bloat_factor 0 {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/llsys_wire_retention_views/r01/llaccel_aux-C/detailed.lef}
write_def {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/llsys_wire_retention_views/r01/llaccel_aux-C/clean.def}
write_verilog {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/llsys_wire_retention_views/r01/llaccel_aux-C/clean.v}
set b [ord::get_db_block];set f [open {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/llsys_wire_retention_views/r01/llaccel_aux-C/pins.tsv} w];puts $f "pin\tdirection\tuse\tnet\tlayer\tx0\ty0\tx1\ty1";foreach p [$b getBTerms] {foreach bp [$p getBPins] {foreach r [$bp getBoxes] {puts $f [join [list [$p getName] [$p getIoType] [$p getSigType] [[$p getNet] getName] [[$r getTechLayer] getName] [$r xMin] [$r yMin] [$r xMax] [$r yMax]] "\t"]}}};close $f
read_sdc {/public/home/yuzelu/PingyangHuang/issue-55/full-block-integration-20261023T103718349596Z/runs/auxiliary-route-llaccel-abc-logic-4c-01/flow/results/nangate45/hpy_llaccel_aux/base/5_1_grt.sdc}
source /OpenROAD-flow-scripts/flow/platforms/nangate45/setRC.tcl
read_spef {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/llsys_wire_pin_retention/r01/extracted.spef}
report_worst_slack -max -digits 6 > {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/llsys_wire_retention_views/r01/llaccel_aux-C/setup.txt}
report_worst_slack -min -digits 6 > {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/llsys_wire_retention_views/r01/llaccel_aux-C/hold.txt}
report_parasitic_annotation -report_unannotated > {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/llsys_wire_retention_views/r01/llaccel_aux-C/parasitic_coverage.txt}
check_setup -verbose > {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/llsys_wire_retention_views/r01/llaccel_aux-C/constraint_coverage.txt}
write_timing_model {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/llsys_wire_retention_views/r01/llaccel_aux-C/timing.lib}
