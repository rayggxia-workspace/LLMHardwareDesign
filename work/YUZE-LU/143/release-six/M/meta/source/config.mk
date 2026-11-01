export PLATFORM = nangate45
export DESIGN_NAME = block_v2_m
export DESIGN_NICKNAME = bv1_block_v2_m
export VERILOG_FILES = /public/home/yuzelu/project-circuit/llm_routing_analysis/worktrees/issue143-seven-block-v2-20261030/outputs/013/pnr/m/input.v
export SDC_FILE = /public/home/yuzelu/project-circuit/llm_routing_analysis/worktrees/issue143-seven-block-v2-20261030/outputs/013/pnr/m/input.sdc
export DIE_AREA = 0 0 930 930
export CORE_AREA = 20 20 910 910
export PLACE_DENSITY = 0.45
export FOOTPRINT_TCL = /public/home/yuzelu/project-circuit/llm_routing_analysis/worktrees/issue143-seven-block-v2-20261030/outputs/013/pnr/m/pins.tcl
export KEEP_VARS = 1
override export MIN_ROUTING_LAYER = metal1
override export MAX_ROUTING_LAYER = metal10

export CAP_MARGIN = 40
export HOLD_SLACK_MARGIN = 0.005
export PRE_GLOBAL_ROUTE_TCL = /public/home/yuzelu/project-circuit/llm_routing_analysis/worktrees/issue143-seven-block-v2-20261030/outputs/013/pnr/m/input-diodes.tcl
export VIA_IN_PIN_MIN_LAYER = metal10
export VIA_IN_PIN_MAX_LAYER = metal10
export DETAILED_ROUTE_ARGS = -via_in_pin_bottom_layer metal10 -via_in_pin_top_layer metal10 -droute_end_iter 64 -verbose 1 -drc_report_iter_step 5 -via_access_layer metal10

export HOLD_SLACK_MARGIN = 0.020
