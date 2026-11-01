set_thread_count 16
read_lef {/OpenROAD-flow-scripts/flow/platforms/nangate45/lef/NangateOpenCellLibrary.tech.lef}
read_def {/public/home/yuzelu/project-circuit/llm_routing_analysis/worktrees/issue143-seven-block-v2-20261030/outputs/136/fragmented.def}
drt::check_drc_cmd fragmented-drc.rpt 0 0 0 0 fragmented_fixture
