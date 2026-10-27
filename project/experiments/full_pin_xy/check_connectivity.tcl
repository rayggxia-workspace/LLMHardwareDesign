read_db $::env(PINXY_CHECK_ODB)
puts "LOGGER_API [info commands ::ord::*] [info commands ::utl::*Logger*] [info commands ::odb::*Logger*]"
if {[catch {odb::orderWires} msg]} {puts "ORDER_SIGNATURE $msg"}
set block [ord::get_db_block]
set db [ord::get_db]
if {[catch {$db getLogger} logger]} {puts "DB_LOGGER_FAIL $logger";exit 1}
if {[catch {odb::orderWires $logger $block} msg]} {puts "ORDER_FAIL $msg";exit 1}
set f [open $::env(PINXY_CONNECT_OUT) w];puts $f "net\titerms\tbterms\tisConnected\tisRCDisconnected"
set bad 0
foreach n [$block getNets] {
  if {[$n getSigType] in {POWER GROUND}} {continue}
  set it [llength [$n getITerms]];set bt [llength [$n getBTerms]]
  puts $f [join [list [$n getName] $it $bt [$n isConnected] [$n isRCDisconnected]] "\t"]
  if {$it+$bt>1 && ![$n isConnected]} {incr bad}
};close $f
puts "ODB_ORDER_CONNECTIVITY_DISCONNECTED $bad"
