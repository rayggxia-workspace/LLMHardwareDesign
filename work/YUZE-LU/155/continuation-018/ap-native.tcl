read_lef /OpenROAD-flow-scripts/flow/platforms/nangate45/lef/NangateOpenCellLibrary.tech.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/nangate45/lef/NangateOpenCellLibrary.macro.mod.lef
read_lef /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-155/m3-abstract-002/bank.lef
read_def /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-155/pin-tracks-003/cts.def
set_thread_count 2
set block [ord::get_db_block]
set tech [[ord::get_db] getTech]
pin_access -via_in_pin_bottom_layer metal10 -via_in_pin_top_layer metal10
exit
