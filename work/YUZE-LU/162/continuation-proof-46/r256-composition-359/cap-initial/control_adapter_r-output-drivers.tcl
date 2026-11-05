set_thread_count 16
read_db {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/r256-fixed-pg-254/2430/delivery/6_final.odb}
set f [open {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/r256-composition-359/cap-initial/control_adapter_r-output-drivers.tsv} w]
foreach port [[ord::get_db_block] getBTerms] {
 if {[$port getIoType] ne "OUTPUT" || [$port getSigType] in {POWER GROUND}} {continue}
 set net [$port getNet];if {$net eq "NULL"} {error "Unconnected native output"}
 set found 0
 foreach term [$net getITerms] {
  set pin [$term getMTerm]
  if {[$pin getIoType] ne "OUTPUT"} {continue}
  incr found;set inst [$term getInst]
  puts $f "[$port getName]\t[$inst getName]\t[[$inst getMaster] getName]\t[$pin getName]\t[$net getName]"
 }
 if {$found!=1} {error "Native output requires exactly one physical driver"}
}
close $f
