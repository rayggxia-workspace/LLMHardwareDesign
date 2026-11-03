read_db {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/pg-strong-delivery-01/control_adapter_g/6_final.odb}
set f [open passive.tsv w]
foreach inst [[ord::get_db_block] getInsts] {
  set master [$inst getMaster]
  if {[$master getName] ne "ANTENNA_X1"} {continue}
  foreach term [$inst getITerms] {
    set definition [$term getMTerm]
    if {[$definition getSigType] in {POWER GROUND}} {continue}
    set net [$term getNet]
    if {$net eq "NULL"} {error "Disconnected passive input"}
    puts $f "[$inst getName]/[$definition getName]\t[$master getName]\t[$master getType]\t[$definition getIoType]\t[$net getName]"
  }
}
close $f
