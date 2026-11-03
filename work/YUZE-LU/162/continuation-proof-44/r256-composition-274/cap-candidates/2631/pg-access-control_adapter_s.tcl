set_thread_count 16
set f [open {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/r256-composition-274/cap-candidates/2631/pg-access.tsv} a]
read_db {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/r256-composition-274/fixed-pg-wrappers/control_adapter_s/wrapper.odb}
set b [ord::get_db_block]
foreach supply {VDD VSS} {set n [$b findNet $supply];set port [$b findBTerm $supply];if {$port eq "NULL" || [$port getNet] ne $n} {error "Actual supply port mismatch"};set count 0
foreach pin [$port getBPins] {foreach box [$pin getBoxes] {if {[[$box getTechLayer] getName] ne "metal10"} {continue};incr count;puts $f "control_adapter_s\t$supply\t[$box xMin]\t[$box yMin]\t[$box xMax]\t[$box yMax]"}}
if {$count!=1} {error "Expected exactly one actual M10 supply interface"}}
close $f
