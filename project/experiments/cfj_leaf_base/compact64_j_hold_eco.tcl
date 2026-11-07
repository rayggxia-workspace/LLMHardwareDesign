# Physical-only ECO for the extracted physical04 J64 input-bit-65 hold path.
# Execute on the already repaired physical04 post-global-route database.
# Do not change SDC, Liberty, functional RTL, or any clock connection.
set block [ord::get_db_block]
set sink [$block findInst {services.rx_boundary.s_req_data[65]$_DFFE_PP_}]
if {$sink eq "NULL"} {
  set sink [$block findInst {services.rx_boundary.s_req_data\[65\]$_DFFE_PP_}]
}
if {$sink eq "NULL"} {error "J64 ECO endpoint not found"}
set pin [$sink findITerm D]
set original [$pin getNet]
if {$original eq "NULL"} {error "J64 ECO endpoint is disconnected"}
set master [[ord::get_db] findMaster BUF_X1]
if {$master eq "NULL"} {error "BUF_X1 not found"}
set location [$sink getLocation]
set previous $original
$pin disconnect
for {set i 0} {$i < 2} {incr i} {
  set name cfj64_hold65_$i
  if {[$block findInst $name] ne "NULL"} {error "ECO already applied"}
  set cell [odb::dbInst_create $block $master $name]
  set net [odb::dbNet_create $block ${name}_z]
  $cell setLocation {*}$location
  $cell setPlacementStatus PLACED
  [$cell findITerm A] connect $previous
  [$cell findITerm Z] connect $net
  set previous $net
  puts "J64_HOLD_ECO $name BUF_X1 at $location"
}
$pin connect $previous
global_connect
foreach name {cfj64_hold65_0 cfj64_hold65_1} {
  set_dont_touch [get_cells $name]
}
detailed_placement_helper
check_placement -verbose
