# Tiny pinned-tool API test. No research macro database is loaded or accepted.
set_thread_count 1
set platform /OpenROAD-flow-scripts/flow/platforms/nangate45
read_lef $platform/lef/NangateOpenCellLibrary.tech.lef
foreach file [lsort [glob $platform/lef/*.lef]] {
 if {[file tail $file] ne "NangateOpenCellLibrary.tech.lef"} {read_lef $file}
}
read_liberty $platform/lib/NangateOpenCellLibrary_typical.lib
set f [open fixture.v w]
puts $f {module api_fixture(input i,output o);BUF_X1 b(.A(i),.Z(o));endmodule}
close $f
read_verilog fixture.v
link_design api_fixture
set block [ord::get_db_block]
set inst [$block findInst b]
if {$inst eq "NULL" || [[$inst getMaster] getName] ne "BUF_X1"} {error "Fixture initial master missing"}
proc fixture_pins {inst} {
 set result {}
 foreach pin [$inst getITerms] {
  set net [$pin getNet]
  lappend result [list [[$pin getMTerm] getName] [expr {$net eq "NULL" ? "NULL" : [$net getName]}]]
 }
 return [lsort $result]
}
set before [fixture_pins $inst]
set location [$inst getLocation]
set result [replace_cell [get_cells [list b]] BUF_X4]
if {$result!=1 || [[$inst getMaster] getName] ne "BUF_X4" || [fixture_pins $inst] ne $before || [$inst getLocation] ne $location} {error "Pinned replace_cell did not preserve DB connectivity/location"}
set sta_inst [sta::get_instance_error instance b]
set liberty_cell [$sta_inst liberty_cell]
puts "STA_CELL=[$liberty_cell name]"
if {[$liberty_cell name] ne "BUF_X4"} {error "STA master not updated with OpenDB"}
if {[replace_cell [get_cells [list b]] AND2_X1]!=0 || [[$inst getMaster] getName] ne "BUF_X4" || [fixture_pins $inst] ne $before} {error "Incompatible-port negative control incorrectly changed fixture"}
write_verilog fixture-after.v
puts "PASS: pinned replace_cell updates STA and OpenDB, preserves all terminals/location, rejects incompatible-port replacement"
