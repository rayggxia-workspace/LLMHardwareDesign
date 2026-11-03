read_liberty {/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib}
read_db {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-166-r-local-state/attempt252/delivery/native/6_final.odb}
set remove {}
foreach lib [[ord::get_db] getLibs] {foreach master [$lib getMasters] {set signal 0;foreach term [$master getMTerms] {if {[$term getSigType] ni {POWER GROUND}} {set signal 1}};if {!$signal} {lappend remove [$master getName]}}}
set f [open {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/r256-native-reuse-249/actual-protection-count.txt} w]
set count 0
foreach inst [[ord::get_db_block] getInsts] {if {[[$inst getMaster] getName] eq "ANTENNA_X1"} {incr count}}
puts $f $count
close $f
write_verilog -remove_cells $remove {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/r256-native-reuse-249/physical-functional.v}
