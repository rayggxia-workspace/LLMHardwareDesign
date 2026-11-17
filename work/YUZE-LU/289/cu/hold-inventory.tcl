read_db $::env(INPUT_ODB)
set f [open $::env(INVENTORY_TSV) w]
puts $f "instance\tmaster"
set counts {}
foreach inst [[ord::get_db_block] getInsts] {
 if {![string match hold* [$inst getName]]} {continue}
 set name [[$inst getMaster] getName]
 puts $f "[$inst getName]\t$name"
 dict incr counts $name
}
close $f
puts "HOLD_CELL_COUNTS $counts"
