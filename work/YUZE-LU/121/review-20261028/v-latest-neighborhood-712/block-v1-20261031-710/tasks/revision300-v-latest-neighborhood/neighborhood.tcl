set_thread_count 16
read_db {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/block-v1-20261031-705/tasks/revision300-v-joint-via-compose/local-candidate.odb}
source {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/block-v1-20261031-710/tasks/revision300-v-latest-neighborhood/region-base.tcl}
source {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/block-v1-20261031-710/src/project/experiments/block_v1/geometry_windows.tcl}
::region::add 0 193340 918810 201480 926880
::region::add 1 233240 2255040 241380 2263110
::region::add 2 313040 151890 321180 159960
::region::add 3 436920 2305370 445060 2313440
::region::add 4 472640 2287240 480780 2295310
::region::add 5 516720 699290 524860 707360
::region::add 6 751940 2463360 760080 2471430
::region::add 7 951440 1022200 959580 1030270
::region::add 8 991340 2314680 999480 2322750
::region::add 9 1115220 412640 1123360 420710
::region::add 10 1554120 228120 1562260 236190
::region::add 11 1669640 2002200 1677780 2010330
::region::add 12 1988840 1208610 1996980 1216680
::region::add 13 1988840 2086410 1996980 2094480
::region::add 14 2068640 2233410 2076780 2241480
::region::add 15 2068640 2418560 2076780 2426630
::region::add 16 2192520 504970 2200660 513040
::region::add 17 2268140 424120 2276280 432190
::region::add 18 2312220 478650 2320360 486720
::region::add 19 2392020 1146240 2400160 1154310
::region::add 20 2471820 681720 2479960 689790
::region::add 21 157050 1833430 165170 1841570
::region::add 22 157050 1909030 165170 1917170
::region::add 23 516170 392830 524290 400970
::region::add 24 710330 2068630 718450 2076770
::region::add 25 868810 233230 876910 241370
::region::add 26 1787960 2148430 1796050 2156570
::region::add 27 1923290 2152630 1931410 2160770
::region::add 28 1932430 1833430 1940530 1841570
::region::add 29 2218570 1270630 2226690 1278770
::region::add 30 2367530 1749430 2375650 1757570

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
