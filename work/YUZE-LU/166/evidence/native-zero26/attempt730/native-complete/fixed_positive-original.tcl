set_thread_count 1
read_lef {/OpenROAD-flow-scripts/flow/platforms/nangate45/lef/NangateOpenCellLibrary.tech.lef}
read_lef {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-166-r-local-state/attempt730/native-complete/fixed-control.lef}
read_def {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-166-r-local-state/attempt730/native-complete/fixed_positive.def}
drt::check_drc_cmd fixed_positive-original.rpt 0 0 0 0 fixed_positive-original
