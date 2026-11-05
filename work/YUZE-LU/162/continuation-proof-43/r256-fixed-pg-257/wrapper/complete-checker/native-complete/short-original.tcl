set_thread_count 16
read_lef {/OpenROAD-flow-scripts/flow/platforms/nangate45/lef/NangateOpenCellLibrary.tech.lef}
read_def {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/r256-fixed-pg-257/wrapper/complete-checker/native-complete/short.def}
drt::check_drc_cmd short-original.rpt 0 0 0 0 short-original
