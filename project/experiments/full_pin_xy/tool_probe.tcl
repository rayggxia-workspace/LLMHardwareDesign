read_db $::env(PINXY_ODB)
foreach cmd {define_pin_shape_pattern set_io_pin_constraint place_pin place_pins global_route detailed_route extract_parasitics check_power_grid report_check_types report_checks write_abstract_lef check_nets} {puts "COMMAND $cmd exists=[llength [info commands $cmd]]"; if {[llength [info commands $cmd]]} {catch {help $cmd} e;puts $e}}
set b [ord::get_db_block]
foreach inst [$b getInsts] {
 if {![[$inst getMaster] isBlock]} {continue}
 puts "MACRO [$inst getName] OBS=[llength [[$inst getMaster] getObstructions]] origin=[[$inst getMaster] getOrigin]"
 catch {set t [$inst getTransform]} e;puts "TRANSFORM $e"
 catch {$t bogus} e;puts "TRANSFORM_METHODS $e"
 set it [odb::dbInstShapeItr]
 catch {$it begin $inst} e;puts "ITERATOR_BEGIN $e"
 set s [odb::dbShape];catch {$it next $s} e;puts "ITERATOR_NEXT $e"
 puts "FIRST_SHAPE [$s xMin] [$s yMin] [$s xMax] [$s yMax]"
 break
}
