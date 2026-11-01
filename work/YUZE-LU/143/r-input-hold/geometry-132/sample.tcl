set_thread_count 16
read_db {/public/home/yuzelu/project-circuit/llm_routing_analysis/worktrees/issue143-seven-block-v2-20261030/outputs/129/candidate.odb}
source {/public/home/yuzelu/project-circuit/llm_routing_analysis/worktrees/issue143-seven-block-v2-20261030/snapshots/132/project/experiments/block_v1/odb_geometry.tcl}
namespace eval bvgeom {variable markers [dict create]}
set context_boxes {}
dict lappend bvgeom::markers metal1 {0 476750 4305030 480850 4309170}
lappend context_boxes {476750 4305030 480850 4309170}
dict lappend bvgeom::markers metal2 {1 75640 1250930 79780 1255000}
lappend context_boxes {75640 1250930 79780 1255000}
dict lappend bvgeom::markers metal3 {2 66350 3271830 70450 3275970}
lappend context_boxes {66350 3271830 70450 3275970}
dict lappend bvgeom::markers metal2 {3 275140 5287970 279280 5292040}
lappend context_boxes {275140 5287970 279280 5292040}
dict lappend bvgeom::markers metal3 {4 778850 478830 782950 482970}
lappend context_boxes {778850 478830 782950 482970}
dict lappend bvgeom::markers metal2 {5 275140 5151890 279280 5155960}
lappend context_boxes {275140 5151890 279280 5155960}
# Load only a sealed database; no repair, connection, placement or write_db.
rename bvgeom::rectangle bvgeom::unfiltered_rectangle
proc bvgeom::rectangle {stream net layer kind object {dx 0} {dy 0} {transform ""}} {
  variable markers
  variable hit
  variable shapes
  variable hits
  incr shapes
  set name [$layer getName]
  if {![dict exists $markers $name]} {return}
  set x0 [expr {[$object xMin]+$dx}];set y0 [expr {[$object yMin]+$dy}]
  set x1 [expr {[$object xMax]+$dx}];set y1 [expr {[$object yMax]+$dy}]
  if {[bvgeom::present $transform]} {
    set xs {};set ys {}
    foreach x [list $x0 $x1] {foreach y [list $y0 $y1] {
      set point [odb::new_Point $x $y];$transform apply $point
      lappend xs [$point getX];lappend ys [$point getY];odb::delete_Point $point
    }}
    set x0 [tcl::mathfunc::min {*}$xs];set x1 [tcl::mathfunc::max {*}$xs]
    set y0 [tcl::mathfunc::min {*}$ys];set y1 [tcl::mathfunc::max {*}$ys]
  }
  if {$x0 >= $x1 || $y0 >= $y1} {error "Degenerate native geometry"}
  foreach marker [dict get $markers $name] {
    lassign $marker index mx0 my0 mx1 my1
    if {$x0 < $mx1 && $mx0 < $x1 && $y0 < $my1 && $my0 < $y1} {
      puts $stream "$index\t$net\t$name\t$kind\t$x0\t$y0\t$x1\t$y1"
      set hit 1;incr hits
    }
  }
}
proc native_hex {text} {binary encode hex [encoding convertto utf-8 $text]}
set block [ord::get_db_block]
if {[$block getDbUnitsPerMicron] != 2000} {error "Native marker units differ"}
set output [open marker-shapes.tsv w]
set terms [open marker-terminals.tsv w]
set itr [odb::new_dbWirePathItr]
set path [odb::new_dbWirePath]
set element [odb::new_dbWirePathShape]
set bvgeom::shapes 0;set bvgeom::hits 0;set nets 0
foreach net [$block getNets] {
  incr nets;set bvgeom::hit 0
  set alias [native_hex [$net getName]]
  set wire [$net getWire]
  if {[bvgeom::present $wire]} {
    $itr begin $wire
    while {[$itr getNextPath $path]} {
      while {[$itr getNextShape $element]} {
        bvgeom::wire_shape $output $alias [odb::dbWirePathShape_shape_get $element]
      }
    }
  }
  foreach special [$net getSWires] {
    foreach box [$special getWires] {
      if {![$box isVia] && [$box getDirection] in {3 OCTILINEAR}} {
        error "Nonrectangular special wire requires an exact polygon exporter"
      }
      bvgeom::db_box $output $alias $box special
    }
  }
  foreach term [$net getBTerms] {
    foreach pin [$term getBPins] {
      foreach box [$pin getBoxes] {bvgeom::db_box $output $alias $box block-port}
    }
  }
  if {$bvgeom::hit} {
    foreach term [$net getBTerms] {
      puts $terms "P\t$alias\t[native_hex [$term getName]]\t[$term getIoType]"
    }
    foreach term [$net getITerms] {
      set inst [$term getInst];set master [$inst getMaster];set mterm [$term getMTerm]
      set box [$inst getBBox]
      puts $terms "I\t$alias\t[native_hex [$inst getName]]\t[native_hex [$master getName]]\t[native_hex [$mterm getName]]\t[$mterm getIoType]\t[$mterm getSigType]\t[$box xMin]\t[$box yMin]\t[$box xMax]\t[$box yMax]"
    }
  }
}
close $output;close $terms
set output [open scan-counts.tsv w]
puts $output "$nets\t$bvgeom::shapes\t$bvgeom::hits"
close $output
odb::delete_dbWirePathShape $element
odb::delete_dbWirePath $path
odb::delete_dbWirePathItr $itr

set output [open marker-shapes.tsv a]
set selected 0
foreach inst [$block getInsts] {
 set box [$inst getBBox];set hit 0
 foreach context $context_boxes {
  lassign $context a b c d
  if {[$box xMin]<$c && $a<[$box xMax] && [$box yMin]<$d && $b<[$box yMax]} {set hit 1;break}
 }
 if {!$hit} {continue}
 incr selected
 set transform [$inst getTransform]
 foreach term [$inst getITerms] {
  set net [$term getNet]
  if {[bvgeom::present $net]} {set alias [native_hex [$net getName]]} else {set alias [native_hex "UNCONNECTED:[$inst getName]/[[$term getMTerm] getName]"]}
  foreach pin [[$term getMTerm] getMPins] {foreach shape [$pin getGeometry] {bvgeom::db_box $output $alias $shape instance-pin $transform}}
 }
 foreach shape [[$inst getMaster] getObstructions] {bvgeom::db_box $output [native_hex "OBS:[$inst getName]"] $shape instance-obs $transform}
}
close $output
puts "SAMPLE_INSTANCES $selected"
