export PLATFORM = nangate45
export DESIGN_NAME = block_v1_r
export DESIGN_NICKNAME = bv1_block_v1_r
export VERILOG_FILES = /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/block-v1-20261101-827/tasks/revision300-route-r/input.v
export SDC_FILE = /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/block-v1-20261101-827/tasks/revision300-route-r/input.sdc
export DIE_AREA = 0 0 2330 2330
export CORE_AREA = 20 20 2310 2310
export PLACE_DENSITY = 0.35
export FOOTPRINT_TCL = /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/block-v1-20261101-827/tasks/revision300-route-r/pins.tcl
export KEEP_VARS = 1
override export MIN_ROUTING_LAYER = metal1
override export MAX_ROUTING_LAYER = metal10

export CAP_MARGIN = 40
export HOLD_SLACK_MARGIN = 0.005
export PRE_GLOBAL_ROUTE_TCL = /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/block-v1-20261101-827/tasks/revision300-route-r/grt-capacity.tcl
export VIA_IN_PIN_MIN_LAYER = metal10
export VIA_IN_PIN_MAX_LAYER = metal10
export DETAILED_ROUTE_ARGS = -via_in_pin_bottom_layer metal10 -via_in_pin_top_layer metal10 -droute_end_iter 64 -verbose 1 -drc_report_iter_step 5 -via_access_layer metal10

export HOLD_SLACK_MARGIN = 0.020
export CTS_ARGS = -sink_clustering_enable -repair_clock_nets -apply_ndr none
export POST_CTS_TCL = /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/block-v1-20261101-827/tasks/revision300-route-r/clock-policy.tcl
export GLOBAL_ROUTE_ARGS = -congestion_iterations 100 -congestion_report_iter_step 5 -verbose
