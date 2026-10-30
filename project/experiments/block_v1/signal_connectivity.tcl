# Read-only, complete signal conductor export. Pin identities are electrodes,
# whereas OBS and POWER/GROUND nets are not part of this signal proof.
source $::env(BV1_GEOMETRY_SOURCE)
proc signal_connectivity_export {destination} {
  set block [ord::get_db_block]
  set stream [open $destination w]
  puts $stream "# SIGNAL-CONNECTIVITY 1 DBU [$block getDbUnitsPerMicron]"
  foreach layer [[[ord::get_db] getTech] getLayers] {
    puts $stream "# LAYER [$layer getName] [$layer getType] [$layer getRoutingLevel]"
  }
  set itr [odb::new_dbWirePathItr]
  set path [odb::new_dbWirePath]
  set element [odb::new_dbWirePathShape]
  set nets 0
  set terms 0
  foreach net [$block getNets] {
    if {[$net getSigType] in {POWER GROUND}} {
      puts $stream "# SKIP [binary encode hex [encoding convertto utf-8 [$net getName]]] [$net getSigType]"
      continue
    }
    incr nets
    set alias n[$net getId]
    puts $stream "# NET $alias [binary encode hex [encoding convertto utf-8 [$net getName]]] [$net getSigType]"
    set wire [$net getWire]
    if {[bvgeom::present $wire]} {
      $itr begin $wire
      while {[$itr getNextPath $path]} {
        while {[$itr getNextShape $element]} {
          bvgeom::wire_shape $stream $alias [odb::dbWirePathShape_shape_get $element]
        }
      }
    }
    foreach special [$net getSWires] {
      foreach box [$special getWires] {
        if {![$box isVia] && [$box getDirection] in {3 OCTILINEAR}} {error "Unsupported signal special wire"}
        bvgeom::db_box $stream $alias $box special
      }
    }
    foreach term [$net getBTerms] {
      incr terms
      set electrode P[binary encode hex [encoding convertto utf-8 [$term getName]]]
      puts $stream "# TERM $electrode"
      foreach pin [$term getBPins] {
        foreach box [$pin getBoxes] {bvgeom::db_box $stream $alias $box $electrode}
      }
    }
    foreach term [$net getITerms] {
      incr terms
      set inst [$term getInst]
      set electrode I[binary encode hex [encoding convertto utf-8 "[$inst getName]/[[$term getMTerm] getName]"]]
      puts $stream "# TERM $electrode"
      set transform [$inst getTransform]
      foreach pin [[$term getMTerm] getMPins] {
        foreach box [$pin getGeometry] {bvgeom::db_box $stream $alias $box $electrode $transform}
      }
    }
  }
  puts $stream "# TOTAL $nets $terms"
  close $stream
  odb::delete_dbWirePathShape $element
  odb::delete_dbWirePath $path
  odb::delete_dbWirePathItr $itr
}
