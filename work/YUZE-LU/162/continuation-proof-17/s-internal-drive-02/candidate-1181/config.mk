export PLATFORM = nangate45
export DESIGN_NAME = block_feed_s_macro
export DESIGN_NICKNAME = bv1_block_feed_s_macro
export VERILOG_FILES = /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/s-internal-drive-02/candidate-1181/input.v
export SDC_FILE = /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/s-internal-drive-02/candidate-1181/input.sdc
export DIE_AREA = 0 0 1680 1680
export CORE_AREA = 20 20 1660 1660
export PLACE_DENSITY = 0.45
export FOOTPRINT_TCL = /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/s-internal-drive-02/candidate-1181/pins.tcl
export KEEP_VARS = 1
export PLACE_DENSITY = 0.4
override export MIN_ROUTING_LAYER = metal1
override export MAX_ROUTING_LAYER = metal10
export REMOVE_ABC_BUFFERS = 1
export GPL_TIMING_DRIVEN = 0
export ENABLE_PLACE_REPAIR_TIMING = 1
export PRE_RESIZE_TCL = /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/s-internal-drive-02/candidate-1181/partition-fanout.tcl

export CAP_MARGIN = 40
export HOLD_SLACK_MARGIN = 0.005
export PRE_GLOBAL_ROUTE_TCL = /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/s-internal-drive-02/candidate-1181/input-diodes.tcl
export VIA_IN_PIN_MIN_LAYER = metal10
export VIA_IN_PIN_MAX_LAYER = metal10
export DETAILED_ROUTE_ARGS = -via_in_pin_bottom_layer metal10 -via_in_pin_top_layer metal10 -droute_end_iter 64 -verbose 1 -drc_report_iter_step 5 -via_access_layer metal10

export HOLD_SLACK_MARGIN = 0.005
