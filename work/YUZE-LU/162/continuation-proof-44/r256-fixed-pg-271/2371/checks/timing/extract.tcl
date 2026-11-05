set_thread_count 16
read_liberty {/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib}
read_db {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/r256-fixed-pg-271/2371/wrapper/wrapper.odb}
read_sdc {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/r256-native-237/2371/gates/deliver/6_final.sdc}
define_process_corner -ext_model_index 0 X
set_extraction_rules_file {/OpenROAD-flow-scripts/flow/platforms/nangate45/rcx_patterns.rules}
extract_parasitics
write_spef {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/r256-fixed-pg-271/2371/checks/timing/6_final.spef}
set f [open passive-inventory.tsv w]
foreach inst [[ord::get_db_block] getInsts] {set master [$inst getMaster];if {[$master getName] ne "ANTENNA_X1"} {continue};foreach term [$inst getITerms] {set def [$term getMTerm];if {[$def getSigType] in {POWER GROUND}} {continue};puts $f "[$inst getName]/[$def getName]\t[$master getName]\t[$master getType]\t[$def getIoType]\t[[$term getNet] getName]"}}
close $f
