set_thread_count 16
read_db {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/block-v1-20261101-903/tasks/revision300-r-current-compose/remaining-candidate.odb}
source {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/block-v1-20261101-903/tasks/revision300-r-current-geometry/region-base.tcl}
source {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/block-v1-20261101-903/src/project/experiments/block_v1/geometry_windows.tcl}
::region::add 0 2032920 3499920 2041060 3507990
::region::add 1 3628920 1242840 3637060 1250910
::region::add 2 611140 1510030 619270 1518170
::region::add 3 3889450 2707030 3897530 2715170
::region::add 4 4317290 3030430 4325410 3038570

rename bvgeom::rectangle bvgeom::original_rectangle
proc bvgeom::rectangle {stream net layer kind object {dx 0} {dy 0} {transform ""}} {
  incr ::region::scanned
  set x0 [expr {[$object xMin]+$dx}];set y0 [expr {[$object yMin]+$dy}]
  set x1 [expr {[$object xMax]+$dx}];set y1 [expr {[$object yMax]+$dy}]
  if {[present $transform]} {
    set xs {};set ys {}
    foreach x [list $x0 $x1] {foreach y [list $y0 $y1] {
      set point [odb::new_Point $x $y];$transform apply $point
      lappend xs [$point getX];lappend ys [$point getY];odb::delete_Point $point
    }}
    set x0 [tcl::mathfunc::min {*}$xs];set x1 [tcl::mathfunc::max {*}$xs]
    set y0 [tcl::mathfunc::min {*}$ys];set y1 [tcl::mathfunc::max {*}$ys]
  }
  foreach index [::region::hits $x0 $y0 $x1 $y1] {
    puts $stream "$index\t$net\t[$layer getName]\t$kind\t$x0\t$y0\t$x1\t$y1"
    dict set ::region::aliases $net 1;incr ::region::emitted
  }
}
bvgeom::export neighborhood.tsv
set block [ord::get_db_block]
set f [open neighborhood.tsv a]
foreach inst [$block getInsts] {
  set boxes [[$inst getMaster] getObstructions]
  if {[llength $boxes]==0} {continue}
  set transform [$inst getTransform]
  foreach box $boxes {bvgeom::db_box $f i[$inst getId] $box instance-obstruction $transform}
}
foreach obs [$block getObstructions] {bvgeom::db_box $f block-obstruction [$obs getBBox] block-obstruction}
close $f
set f [open net-aliases.tsv w]
foreach net [$block getNets] {set alias n[$net getId]
  if {[dict exists $::region::aliases $alias]} {puts $f "$alias\t[binary encode hex [encoding convertto utf-8 [$net getName]]]"}
}
close $f
set f [open scan-counts.tsv w];puts $f "$::region::scanned\t$::region::emitted";close $f
set tech [ord::get_db_tech]
set f [open layer-dimensions.tsv w]
foreach layer [$tech getLayers] {puts $f "[$layer getName]\t[$layer getWidth]\t[$layer getSpacing]"}
close $f
set f [open via-footprints.tsv w]
foreach via [$tech getVias] {
  foreach box [$via getBoxes] {puts $f "[$via getName]\t[[$box getTechLayer] getName]\t[$box xMin]\t[$box yMin]\t[$box xMax]\t[$box yMax]"}
}
close $f
