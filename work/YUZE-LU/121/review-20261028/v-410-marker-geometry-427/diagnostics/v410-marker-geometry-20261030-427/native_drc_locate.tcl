# Load only a sealed database; no repair, connection, placement or write_db.
rename bvgeom::rectangle bvgeom::unfiltered_rectangle
proc bvgeom::rectangle {stream net layer kind object {dx 0} {dy 0} {transform ""}} {
  variable markers
  variable hit
  variable shapes
  variable hits
  if {$transform ne ""} {error "This locator does not transform cell pin geometry"}
  incr shapes
  set name [$layer getName]
  if {![dict exists $markers $name]} {return}
  set x0 [expr {[$object xMin]+$dx}];set y0 [expr {[$object yMin]+$dy}]
  set x1 [expr {[$object xMax]+$dx}];set y1 [expr {[$object yMax]+$dy}]
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
