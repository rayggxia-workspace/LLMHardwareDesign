# Read-only tool/API probe. No write_db or geometry/logic mutation.
# env HPY_PROBE_ODB=/absolute/input.odb openroad -exit migration_probe.tcl
if {![info exists ::env(HPY_PROBE_ODB)]} {error "HPY_PROBE_ODB is required"}
puts "HPY_PROBE_INPUT $::env(HPY_PROBE_ODB)"
foreach command {set_nets_to_route set_routing_layers global_route detailed_route pin_access check_drc extract_parasitics write_spef read_spef check_antennas check_power_grid read_def write_def} {
  puts "HPY_COMMAND $command [expr {[llength [info commands $command]] != 0}]"
  if {[llength [info commands $command]]} {
    set code [catch {help $command} result]
    puts "HPY_HELP_RESULT $command $code $result"
  }
}
foreach pattern {odb::dbNet_setWireType odb::dbWire_set* odb::dbWire_get* odb::dbWireEncoder* odb::dbWireDecoder* grt::*net*route* drt::*check*drc*} {
  puts "HPY_API $pattern [info commands $pattern]"
}
foreach name {set_nets_to_route detailed_route read_def} {
  if {[llength [info procs $name]]} {
    puts "HPY_PROC_BEGIN $name"
    puts [info body $name]
    puts "HPY_PROC_END $name"
  }
}
foreach path {
  /OpenROAD-flow-scripts/tools/OpenROAD/src/drt/src/io/io.cpp
  /OpenROAD/src/drt/src/io/io.cpp
  /OpenROAD-flow-scripts/tools/OpenROAD/src/grt/src/GlobalRouter.cpp
} {
  puts "HPY_SOURCE_EXISTS $path [file isfile $path]"
}
read_db $::env(HPY_PROBE_ODB)
set block [ord::get_db_block]
set decoder [odb::dbWireDecoder]
set printed 0
foreach net [$block getNets] {
  if {[$net getSigType] in {POWER GROUND}} {continue}
  set wire [$net getWire]
  if {$wire eq "NULL"} {continue}
  $decoder begin $wire
  set op [$decoder next]
  puts "HPY_NET_READONLY name=[$net getName] declared_type=[$net getWireType] first_op=$op encoded_type=[$decoder getWireType] length=[$wire getLength]"
  incr printed
  if {$printed >= 3} {break}
}
odb::delete_dbWireDecoder $decoder
puts "HPY_PROBE_COMPLETE instances=[llength [$block getInsts]] nets=[llength [$block getNets]] mutation=none"
