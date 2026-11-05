set_thread_count 16
read_db {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/s-ready-qualified-01/1391/pg-delivery/6_final.odb}
set f [open {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/s-ready-composition-01/1391/strong-local-native-pin-load-197/control_adapter_s/pins.tsv} w]

foreach port [[ord::get_db_block] getBTerms] {
 if {[$port getSigType] in {POWER GROUND}} {continue}
 set net [$port getNet];if {$net eq "NULL"} {error "Disconnected actual boundary"}
 puts $f "PORT\t[$port getName]"
 foreach term [$net getITerms] {
  set pin [$term getMTerm]
  if {[$pin getSigType] in {POWER GROUND}} {continue}
  if {[$pin getIoType] ne "INPUT"} {continue}
  set inst [$term getInst]
  puts $f "PIN\t[$port getName]\t[$inst getName]\t[[$inst getMaster] getName]\t[$pin getName]"
 }
}
close $f
