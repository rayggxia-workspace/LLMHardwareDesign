read_db $::env(COUPLING_DRIVER_ODB)
set file [open $::env(COUPLING_DRIVER_TSV) w]
foreach port [[ord::get_db_block] getBTerms] {
  if {[$port getIoType] ne "OUTPUT"} {continue}
  set net [$port getNet]
  foreach terminal [$net getITerms] {
    set pin [$terminal getMTerm]
    if {[$pin getIoType] ne "OUTPUT"} {continue}
    set inst [$terminal getInst]
    set master [$inst getMaster]
    puts $file "[binary encode hex [encoding convertto utf-8 [$port getName]]]\t[[$inst getMaster] getName]\t[binary encode hex [encoding convertto utf-8 [$pin getName]]]\t[$master getType]\t[binary encode hex [encoding convertto utf-8 [$inst getName]]]"
  }
}
close $file
