# Read-only interconnect/pin geometry. OBS are keepouts, not conductors.
# Macro internals require their separately frozen leaf databases.
namespace eval bvgeom {
proc present {object} { expr {$object ne "NULL" && $object ne ""} }
proc rectangle {stream net layer kind object {dx 0} {dy 0} {transform ""}} {
  set x0 [expr {[$object xMin]+$dx}]
  set y0 [expr {[$object yMin]+$dy}]
  set x1 [expr {[$object xMax]+$dx}]
  set y1 [expr {[$object yMax]+$dy}]
  if {[present $transform]} {
    set xs {}; set ys {}
    foreach x [list $x0 $x1] {
      foreach y [list $y0 $y1] {
        set point [odb::new_Point $x $y]
        $transform apply $point
        lappend xs [$point getX]; lappend ys [$point getY]
        odb::delete_Point $point
      }
    }
    set x0 [tcl::mathfunc::min {*}$xs]; set x1 [tcl::mathfunc::max {*}$xs]
    set y0 [tcl::mathfunc::min {*}$ys]; set y1 [tcl::mathfunc::max {*}$ys]
  }
  if {$x0 >= $x1 || $y0 >= $y1} { error "Degenerate conductor rectangle" }
  puts $stream "$net\t[$layer getName]\t$kind\t$x0\t$y0\t$x1\t$y1"
}
proc db_box {stream net box kind {transform ""}} {
  if {[$box isVia]} {
    set via [$box getTechVia]
    if {![present $via]} { set via [$box getBlockVia] }
    if {![present $via]} { error "Unresolved box via" }
    lassign [$box getViaXY] x y
    foreach part [$via getBoxes] {
      rectangle $stream $net [$part getTechLayer] $kind-via $part $x $y $transform
    }
  } else {
    rectangle $stream $net [$box getTechLayer] $kind $box 0 0 $transform
  }
}
proc wire_shape {stream net shape} {
  if {[$shape isVia]} {
    set via [$shape getTechVia]
    if {![present $via]} { set via [$shape getVia] }
    if {![present $via]} { error "Unresolved wire via" }
    lassign [$shape getViaXY] x y
    foreach box [$via getBoxes] {
      rectangle $stream $net [$box getTechLayer] wire-via $box $x $y
    }
  } else {
    rectangle $stream $net [$shape getTechLayer] wire $shape
  }
}
proc export {destination} {
  set block [ord::get_db_block]
  set output [open $destination w]
  puts $output "# block-v1-odb-geometry/1 dbu_per_um=[$block getDbUnitsPerMicron]"
  set itr [odb::dbWirePathItr]
  set path [odb::dbWirePath]
  set element [odb::dbWirePathShape]
  foreach net [$block getNets] {
    set alias n[$net getId]
    puts $output "# NET $alias [binary encode hex [encoding convertto utf-8 [$net getName]]]"
    set wire [$net getWire]
    if {[present $wire]} {
      $itr begin $wire
      while {[$itr getNextPath $path]} {
        while {[$itr getNextShape $element]} {
          wire_shape $output $alias [odb::dbWirePathShape_shape_get $element]
        }
      }
    }
    foreach special [$net getSWires] {
      foreach box [$special getWires] {
        if {![$box isVia] && [$box getDirection] in {3 OCTILINEAR}} {
          error "Nonrectangular special wire requires an exact polygon exporter"
        }
        db_box $output $alias $box special
      }
    }
    foreach term [$net getBTerms] {
      foreach pin [$term getBPins] {
        foreach box [$pin getBoxes] {
          db_box $output $alias $box block-port
        }
      }
    }
    foreach term [$net getITerms] {
      set inst [$term getInst]
      set transform [$inst getTransform]
      foreach pin [[$term getMTerm] getMPins] {
        foreach box [$pin getGeometry] {
          db_box $output $alias $box instance-pin $transform
        }
      }
    }
  }
  close $output
  odb::delete_dbWirePathShape $element
  odb::delete_dbWirePath $path
  odb::delete_dbWirePathItr $itr
}
}
