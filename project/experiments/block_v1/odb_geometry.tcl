# Read-only, exact wire/via and block-port geometry. OBS are keepouts, not
# conductors. Instance pin geometry is deliberately rejected until qualified.
namespace eval bvgeom {
proc present {object} { expr {$object ne "NULL" && $object ne ""} }
proc rectangle {stream net layer kind object {dx 0} {dy 0}} {
  set x0 [expr {[$object xMin]+$dx}]
  set y0 [expr {[$object yMin]+$dy}]
  set x1 [expr {[$object xMax]+$dx}]
  set y1 [expr {[$object yMax]+$dy}]
  if {$x0 >= $x1 || $y0 >= $y1} { error "Degenerate conductor rectangle" }
  puts $stream "$net\t[$layer getName]\t$kind\t$x0\t$y0\t$x1\t$y1"
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
  if {[llength [$block getInsts]]} { error "Instance-pin exporter not yet qualified" }
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
    if {[llength [$net getSWires]]} { error "Special-wire exporter not yet qualified" }
    foreach term [$net getBTerms] {
      foreach pin [$term getBPins] {
        foreach box [$pin getBoxes] {
          if {[$box isVia]} { error "Block-port via exporter not yet qualified" }
          rectangle $output $alias [$box getTechLayer] block-port $box
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
