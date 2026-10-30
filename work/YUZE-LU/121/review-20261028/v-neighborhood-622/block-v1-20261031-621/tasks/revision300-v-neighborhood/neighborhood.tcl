set_thread_count 16
read_db {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/block-v1-20261031-613/tasks/revision300-v-transition-filter/transition-batch.odb}
source {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/block-v1-20261031-621/tasks/revision300-v-neighborhood/region-base.tcl}
namespace eval region {variable windows {};variable aliases {};variable scanned 0;variable hits 0}
lappend region::windows [list 0 102350 1673830 110450 1681970]
lappend region::windows [list 1 103850 1514230 111970 1522370]
lappend region::windows [list 2 125910 476830 133970 484970]
lappend region::windows [list 3 131290 1749430 139330 1757570]

rename bvgeom::rectangle bvgeom::original_rectangle
proc bvgeom::rectangle {stream net layer kind object {dx 0} {dy 0} {transform ""}} {
  incr region::scanned
  set name [$layer getName]
  if {$name ni {metal1 metal2 metal3 metal4 metal5 metal6 via1 via2 via3 via4 via5}} {return}
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
  if {$x0 >= $x1 || $y0 >= $y1} {error "Degenerate region shape"}
  foreach w $region::windows {
    lassign $w index a b c d
    if {$x0 < $c && $a < $x1 && $y0 < $d && $b < $y1} {
      puts $stream "$index\t$net\t$name\t$kind\t$x0\t$y0\t$x1\t$y1"
      dict set region::aliases $net 1;incr region::hits
    }
  }
}
bvgeom::export neighborhood.tsv
set block [ord::get_db_block]
set f [open neighborhood.tsv a]
foreach inst [$block getInsts] {
  set box [$inst getBBox];set overlaps 0
  foreach w $region::windows {lassign $w index a b c d
    if {[$box xMin] < $c && $a < [$box xMax] && [$box yMin] < $d && $b < [$box yMax]} {set overlaps 1;break}
  }
  if {!$overlaps} {continue}
  set transform [$inst getTransform]
  foreach box [[$inst getMaster] getObstructions] {bvgeom::db_box $f i[$inst getId] $box instance-obstruction $transform}
}
foreach obstruction [$block getObstructions] {bvgeom::db_box $f block-obstruction [$obstruction getBBox] block-obstruction}
close $f
set f [open net-aliases.tsv w]
foreach net [$block getNets] {set alias n[$net getId]
  if {[dict exists $region::aliases $alias]} {puts $f "$alias\t[binary encode hex [encoding convertto utf-8 [$net getName]]]"}
}
close $f
set f [open scan-counts.tsv w];puts $f "$region::scanned\t$region::hits";close $f
set tech [ord::get_db_tech]
set f [open layer-dimensions.tsv w]
foreach name {metal1 metal2 metal3 metal4 metal5 metal6} {set layer [$tech findLayer $name];puts $f "$name\t[$layer getWidth]\t[$layer getSpacing]"}
close $f
set f [open via-footprints.tsv w]
set via [$tech findVia via1_4];if {$via eq "NULL" || $via eq ""} {error "Missing actual via"}
foreach box [$via getBoxes] {puts $f "via1_4	[[$box getTechLayer] getName]	[$box xMin]	[$box yMin]	[$box xMax]	[$box yMax]"}
set via [$tech findVia via1_7];if {$via eq "NULL" || $via eq ""} {error "Missing actual via"}
foreach box [$via getBoxes] {puts $f "via1_7	[[$box getTechLayer] getName]	[$box xMin]	[$box yMin]	[$box xMax]	[$box yMax]"}
set via [$tech findVia via2_5];if {$via eq "NULL" || $via eq ""} {error "Missing actual via"}
foreach box [$via getBoxes] {puts $f "via2_5	[[$box getTechLayer] getName]	[$box xMin]	[$box yMin]	[$box xMax]	[$box yMax]"}
set via [$tech findVia via3_2];if {$via eq "NULL" || $via eq ""} {error "Missing actual via"}
foreach box [$via getBoxes] {puts $f "via3_2	[[$box getTechLayer] getName]	[$box xMin]	[$box yMin]	[$box xMax]	[$box yMax]"}
set via [$tech findVia via4_0];if {$via eq "NULL" || $via eq ""} {error "Missing actual via"}
foreach box [$via getBoxes] {puts $f "via4_0	[[$box getTechLayer] getName]	[$box xMin]	[$box yMin]	[$box xMax]	[$box yMax]"}
set via [$tech findVia via5_0];if {$via eq "NULL" || $via eq ""} {error "Missing actual via"}
foreach box [$via getBoxes] {puts $f "via5_0	[[$box getTechLayer] getName]	[$box xMin]	[$box yMin]	[$box xMax]	[$box yMax]"}
close $f
