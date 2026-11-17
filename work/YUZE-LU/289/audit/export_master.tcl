# Read-only master contract export. Parent scheduler runs with EDA environment.
read_db $::env(AUDIT_PARENT_ODB)
set m [[ord::get_db] findMaster $::env(AUDIT_MASTER)]
if {$m eq "NULL"} {error "Required master not found"}
set f [open $::env(AUDIT_MASTER_OUT) w]
puts $f [join [list MASTER [$m getName] [$m getWidth] [$m getHeight]] "\t"]
foreach mt [$m getMTerms] {
 puts $f [join [list TERM [$mt getName] [$mt getIoType] [$mt getSigType]] "\t"]
 foreach mp [$mt getMPins] {
  foreach b [$mp getGeometry] {
   puts $f [join [list PIN [$mt getName] [[$b getTechLayer] getName] [$b xMin] [$b yMin] [$b xMax] [$b yMax]] "\t"]
  }
 }
}
foreach b [$m getObstructions] {
 puts $f [join [list OBS [[$b getTechLayer] getName] [$b xMin] [$b yMin] [$b xMax] [$b yMax]] "\t"]
}
close $f
puts MASTER_CONTRACT_EXPORTED
