set_thread_count 16
read_db {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-166-r-local-state/attempt428/physical/flow/results/nangate45/r166_1024/base/6_final.odb}
set cells [dict create]
foreach net [[ord::get_db_block] getNets] {
 if {[$net getSigType] eq "CLOCK"} {foreach term [$net getITerms] {set inst [$term getInst];dict set cells [$inst getName] 1}}
}
set f [open {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-166-r-local-state/attempt516/physical/CLOCK_NATIVE_NAMES.tsv} w]
foreach name [lsort [dict keys $cells]] {puts $f $name}
close $f
set found [dict create]
foreach cell [get_cells -hierarchical *] {
 set inst [sta::sta_to_db_inst $cell]
 if {$inst ne "NULL"} {set name [$inst getName];if {[dict exists $cells $name]} {dict set found $name 1}}
}
if {[dict size $found]!=[dict size $cells]} {error "Source ODB/STA clock instance names differ"}
puts "R166_SOURCE_CLOCK_NAMES; native=[dict size $cells]; STA=[dict size $found]; exact_names=1"
