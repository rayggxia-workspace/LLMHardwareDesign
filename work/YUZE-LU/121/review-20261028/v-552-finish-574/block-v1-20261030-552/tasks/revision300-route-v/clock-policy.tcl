set f [open [file join $::env(RESULTS_DIR) bv1-clock-policy.tsv] w]
foreach net [[ord::get_db_block] getNets] {
  if {[$net getSigType] ne "CLOCK"} {continue}
  if {[$net getNonDefaultRule] ne "NULL"} {error "Unexpected clock NDR: [$net getName]"}
  puts $f "[$net getName]\tnone"
}
close $f
