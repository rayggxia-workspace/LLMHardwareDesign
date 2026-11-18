# Read-only inventory. Run inside allocated compute node/container.
read_db $::env(INPUT_ODB)
set block [ord::get_db_block]
set out [open $::env(INVENTORY_TSV) w]
puts $out "port\tdirection\tnet\tinstance\tmaster\tmaster_type\tterminal\tterminal_direction\tx_dbu\ty_dbu\tproposed_x8\tmaster_exists"
foreach port [$block getBTerms] {
 set net [$port getNet]
 if {$net eq "NULL"} {continue}
 foreach term [$net getITerms] {
  set inst [$term getInst]
  set master [$inst getMaster]
  set mt [$term getMTerm]
  lassign [$inst getLocation] x y
  set old [$master getName]
  set proposed ""
  set exists 0
  if {[regexp {^(BUF|INV|CLKBUF)_X([0-9]+)$} $old -> family size]} {
   if {$size < 8} {set proposed ${family}_X8} else {set proposed $old}
   set exists [expr {[[ord::get_db] findMaster $proposed] ne "NULL"}]
  }
  puts $out [join [list [$port getName] [$port getIoType] [$net getName] [$inst getName] $old [$master getType] [$mt getName] [$mt getIoType] $x $y $proposed $exists] "\t"]
 }
}
close $out
puts INVENTORY_COMPLETE
