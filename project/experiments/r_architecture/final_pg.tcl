# Repair only added-buffer power connectivity before final extraction/reporting.
# global_connect -force still skips protected instances in this tool build.
unset_dont_touch [get_cells r157_io_*]
add_global_connection -net VDD -inst_pattern {r157_io_.*} -pin_pattern {VDD} -power
add_global_connection -net VSS -inst_pattern {r157_io_.*} -pin_pattern {VSS} -ground
global_connect
set n 0
foreach inst [[ord::get_db_block] getInsts] {
 if {![string match {r157_io_*} [$inst getName]]} {continue}
 foreach pg {VDD VSS} {
  set pin [$inst findITerm $pg]
  if {$pin eq "NULL" || [$pin getNet] eq "NULL" || [[$pin getNet] getName] ne $pg} {error "unconnected added buffer supply: [$inst getName]/$pg"}
 }
 incr n
}
if {$n != 168} {error "unexpected added buffer count: $n"}
set_dont_touch [get_cells r157_io_*]
puts "R157_FINAL_PG_CONNECTED=$n"
