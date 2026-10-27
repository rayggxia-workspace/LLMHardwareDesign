# A real GRT checkpoint supplies the GCELLGRID required by this binary.
# It is read only; no grid/rule/physical geometry is fabricated or changed.
read_db $::env(PINXY_DRC_ODB)
set count 0
foreach n [[ord::get_db_block] getNets] {
  if {[$n getSigType] ni {POWER GROUND} && [$n getWire] ne "NULL"} {incr count}
}
set f [open $::env(PINXY_PREFLIGHT_STATE) w]
puts $f "signal_nets_with_dbWire\t$count";close $f
set_routing_layers -signal metal2-metal10 -clock metal4-metal10
drt::check_drc -output_file $::env(PINXY_DRC_OUT)
puts "PARENT_FIXED_PREFLIGHT_NATIVE_EXECUTED"
