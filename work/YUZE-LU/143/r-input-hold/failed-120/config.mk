export PLATFORM = nangate45
export DESIGN_NAME = block_v1_r
export DESIGN_NICKNAME = bv1_block_v1_r
export VERILOG_FILES = /public/home/yuzelu/project-circuit/llm_routing_analysis/worktrees/issue143-seven-block-v2-20261030/outputs/120/pnr/r/input.v
export SDC_FILE = /public/home/yuzelu/project-circuit/llm_routing_analysis/worktrees/issue143-seven-block-v2-20261030/outputs/120/pnr/r/input.sdc
export DIE_AREA = 0 0 3000 3000
export CORE_AREA = 20 20 2980 2980
export PLACE_DENSITY = 0.45
export FOOTPRINT_TCL = /public/home/yuzelu/project-circuit/llm_routing_analysis/worktrees/issue143-seven-block-v2-20261030/outputs/120/pnr/r/pins.tcl
export KEEP_VARS = 1
override export MIN_ROUTING_LAYER = metal1
override export MAX_ROUTING_LAYER = metal10
export PLACE_DENSITY = 0.25
export CTS_ARGS = -sink_clustering_enable -repair_clock_nets -apply_ndr none

export CAP_MARGIN = 40
export HOLD_SLACK_MARGIN = 0.005
export PRE_GLOBAL_ROUTE_TCL = /public/home/yuzelu/project-circuit/llm_routing_analysis/worktrees/issue143-seven-block-v2-20261030/outputs/120/pnr/r/input-diodes.tcl
export VIA_IN_PIN_MIN_LAYER = metal10
export VIA_IN_PIN_MAX_LAYER = metal10
export DETAILED_ROUTE_ARGS = -via_in_pin_bottom_layer metal10 -via_in_pin_top_layer metal10 -droute_end_iter 64 -verbose 1 -drc_report_iter_step 5 -via_access_layer metal10

export HOLD_SLACK_MARGIN = 0.020

# Measured final RC deficits: setup164ps / hold109ps. Optimization only; no SDC exception.
export SETUP_SLACK_MARGIN = 0.200
export HOLD_SLACK_MARGIN = 0.020
export PRE_GLOBAL_ROUTE_TCL = /public/home/yuzelu/project-circuit/llm_routing_analysis/worktrees/issue143-seven-block-v2-20261030/outputs/120/pnr/r/r-input-hold-guard.tcl

# Measured final RC deficits: setup164ps / hold109ps. Optimization only; no SDC exception.
export SETUP_SLACK_MARGIN = 0.250
export HOLD_SLACK_MARGIN = 0.020
export PRE_GLOBAL_ROUTE_TCL = /public/home/yuzelu/project-circuit/llm_routing_analysis/worktrees/issue143-seven-block-v2-20261030/outputs/120/pnr/r/r-input-hold-guard.tcl
export POST_GLOBAL_ROUTE_TCL = /public/home/yuzelu/project-circuit/llm_routing_analysis/worktrees/issue143-seven-block-v2-20261030/outputs/120/pnr/r/r-measured-hold.tcl

# Measured final RC deficits: setup164ps / hold109ps. Optimization only; no SDC exception.
export SETUP_SLACK_MARGIN = 0.250
export HOLD_SLACK_MARGIN = 0.020
export PRE_GLOBAL_ROUTE_TCL = 
export SKIP_INCREMENTAL_REPAIR = 1
export OPT_POST_GRT_WNS = 1
export POST_GLOBAL_ROUTE_TCL = /public/home/yuzelu/project-circuit/llm_routing_analysis/worktrees/issue143-seven-block-v2-20261030/outputs/120/pnr/r/r-targeted-closure.tcl
