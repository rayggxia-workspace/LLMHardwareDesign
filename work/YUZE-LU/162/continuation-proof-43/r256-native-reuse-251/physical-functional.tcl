read_liberty {/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib}
read_db {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-166-r-local-state/attempt252/delivery/native/6_final.odb}
set remove {}
foreach lib [[ord::get_db] getLibs] {foreach master [$lib getMasters] {set signal 0;foreach term [$master getMTerms] {if {[$term getSigType] ni {POWER GROUND}} {set signal 1}};if {!$signal} {lappend remove [$master getName]}}}
set f [open {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/r256-native-reuse-251/actual-protection-count.txt} w]
set count 0
foreach inst [[ord::get_db_block] getInsts] {if {[[$inst getMaster] getName] eq "ANTENNA_X1"} {incr count}}
puts $f $count
close $f
write_verilog -remove_cells $remove {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/r256-native-reuse-251/physical-functional.v}
set f [open {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/r256-native-reuse-251/actual-signal-pins.tsv} w]
foreach term [[ord::get_db_block] getBTerms] {if {[$term getSigType] in {POWER GROUND}} {continue};foreach pin [$term getBPins] {foreach box [$pin getBoxes] {puts $f "[$term getName]\t[[$box getTechLayer] getName]\t[$box xMin]\t[$box yMin]\t[$box xMax]\t[$box yMax]"}}}
close $f
