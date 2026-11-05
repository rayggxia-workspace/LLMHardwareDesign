set_thread_count 16
read_lef {/OpenROAD-flow-scripts/flow/platforms/nangate45/lef/NangateOpenCellLibrary.tech.lef}
read_def {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/r256-fixed-pg-272/wrapper/complete-checker/native-complete/notch.def}
drt::check_drc_cmd notch.rpt 0 0 0 0 notch
