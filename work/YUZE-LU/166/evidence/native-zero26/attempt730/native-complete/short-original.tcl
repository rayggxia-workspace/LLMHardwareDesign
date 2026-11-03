set_thread_count 1
read_lef {/OpenROAD-flow-scripts/flow/platforms/nangate45/lef/NangateOpenCellLibrary.tech.lef}
read_def {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-166-r-local-state/attempt730/native-complete/short.def}
drt::check_drc_cmd short-original.rpt 0 0 0 0 short-original
