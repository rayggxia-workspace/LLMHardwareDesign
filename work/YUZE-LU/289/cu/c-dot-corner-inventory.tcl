set_thread_count 2
help set_placement_padding
help create_placement_blockage
help detailed_placement
read_db /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/runs/C-v22-access-metal1/flow/results/nangate45/c-overlay-current/base/6_final.odb
set b [ord::get_db_block]
set out [open /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/dot-corner-instances.tsv w]
puts $out "name\tmaster\tstatus\tx1\ty1\tx2\ty2\tblock"
foreach i [$b getInsts] {
 set box [$i getBBox]
 if {[$box xMax] < 3976000 || [$box xMin] > 4024000 || [$box yMax] < 1312000 || [$box yMin] > 1360000} {continue}
 puts $out "[$i getName]\t[[$i getMaster] getName]\t[$i getPlacementStatus]\t[$box xMin]\t[$box yMin]\t[$box xMax]\t[$box yMax]\t[[$i getMaster] isBlock]"
}
close $out
puts DOT_CORNER_INVENTORY_COMPLETE