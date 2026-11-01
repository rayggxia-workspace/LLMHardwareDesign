# Read actual driver chains for the two unmatched C8 outputs and two controls.
read_liberty /OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib
read_db $::env(BV1_BOUNDARY_ODB)
set block [ord::get_db_block]
proc bv1_trace_net {net depth seen} {
  if {$depth>30 || [dict exists $seen [$net getId]]} {error "Driver cycle or excessive depth"}
  dict set seen [$net getId] 1
  puts "NET\t$depth\t[$net getName]\t[$net getSigType]"
  foreach term [$net getITerms] {
    set mt [$term getMTerm]
    if {[$mt getSigType] in {POWER GROUND} || [$mt getIoType] ni {OUTPUT INOUT}} {continue}
    set inst [$term getInst]
    set master [$inst getMaster]
    puts "DRIVER\t$depth\t[$inst getName]\t[$master getName]\t[$master getType]\t[$mt getName]"
    if {[string match BUF_X* [$master getName]] || [string match CLKBUF_X* [$master getName]]} {
      set input [$inst findITerm A]
      if {$input eq "NULL" || [$input getNet] eq "NULL"} {error "Missing actual buffer input"}
      bv1_trace_net [$input getNet] [expr {$depth+1}] $seen
    }
  }
}
foreach name {{adebug[6]} {mdebug[4]} {adebug[5]} {mdebug[3]}} {
  set port [$block findBTerm $name]
  if {$port eq "NULL" || [$port getNet] eq "NULL"} {error "Target port is absent"}
  puts "PORT\t$name\t[$port getIoType]\t[$port getSigType]"
  bv1_trace_net [$port getNet] 0 [dict create]
}
foreach name {LOGIC0_X1 LOGIC1_X1} {
  set master [[ord::get_db] findMaster $name]
  if {$master ne "NULL"} {puts "MASTER\t$name\t[$master getType]"}
}
