export PLATFORM = nangate45
export DESIGN_NAME = g_s32
export DESIGN_NICKNAME = bv1_g_s32
export VERILOG_FILES = /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-250-g-physical-20261111-04/route/input.v
export SDC_FILE = /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-250-g-physical-20261111-04/route/input.sdc
export DIE_AREA = 0 0 240 240
export CORE_AREA = 16 16 224 224
export PLACE_DENSITY = 0.68
export FOOTPRINT_TCL = /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-250-g-physical-20261111-04/route/pins.tcl
export KEEP_VARS = 1
override export MIN_ROUTING_LAYER = metal1
override export MAX_ROUTING_LAYER = metal10

export CAP_MARGIN = 40
export HOLD_SLACK_MARGIN = 0.005
export PRE_GLOBAL_ROUTE_TCL = /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-250-g-physical-20261111-04/route/input-diodes.tcl
export VIA_IN_PIN_MIN_LAYER = metal10
export VIA_IN_PIN_MAX_LAYER = metal10
export DETAILED_ROUTE_ARGS = -via_in_pin_bottom_layer metal10 -via_in_pin_top_layer metal10 -droute_end_iter 64 -verbose 1 -drc_report_iter_step 5 -via_access_layer metal10

export HOLD_SLACK_MARGIN = 0.020
