# Exact read-only wire/via/pin boxes. Non-selected nets retain all M9/M10/via9
# conductors, including special PG. Selected nets retain the complete stack.
source $::env(BV1_GEOMETRY_SOURCE)
rename bvgeom::rectangle bvgeom::unfiltered_rectangle
proc bvgeom::rectangle {stream net layer kind object {dx 0} {dy 0} {transform ""}} {
  if {!$::escape_selected && [$layer getName] ni {metal9 metal10 via9}} {return}
  bvgeom::unfiltered_rectangle $stream $net $layer $kind $object $dx $dy $transform
}
proc escape_hex {text} {binary encode hex [encoding convertto utf-8 $text]}
proc escape_geometry {destination names} {
  set block [ord::get_db_block]
  if {[$block getDbUnitsPerMicron] != 2000} {error "Unexpected native units"}
  set stream [open $destination w]
  set itr [odb::new_dbWirePathItr]
  set path [odb::new_dbWirePath]
  set element [odb::new_dbWirePathShape]
  # Do not silently omit possible upper-layer master pin conductors.
  set high_master 0
  foreach master [[ord::get_db] getLibs] {
    foreach cell [$master getMasters] {
      foreach term [$cell getMTerms] {
        foreach pin [$term getMPins] {
          foreach box [$pin getGeometry] {
            if {[$box isVia] || [[$box getTechLayer] getName] in {metal9 metal10}} {set high_master 1}
          }
        }
      }
    }
  }
  foreach net [$block getNets] {
    set name [$net getName]
    set ::escape_selected [expr {[lsearch -exact $names $name] >= 0}]
    set alias [escape_hex $name]
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
        if {![$box isVia] && [$box getDirection] in {3 OCTILINEAR}} {error "Unsupported special wire"}
        bvgeom::db_box $stream $alias $box special
      }
    }
    foreach term [$net getBTerms] {
      foreach pin [$term getBPins] {
        foreach box [$pin getBoxes] {bvgeom::db_box $stream $alias $box P-[escape_hex [$term getName]]}
      }
    }
    if {$::escape_selected || $high_master} {
      foreach term [$net getITerms] {
        set inst [$term getInst]
        foreach pin [[$term getMTerm] getMPins] {
          foreach box [$pin getGeometry] {
            if {$::escape_selected && ([$box isVia] || [[$box getTechLayer] getName] in {metal9 metal10})} {
              error "Selected net has a native upper-layer cell anchor; unsupported rewrite"
            }
            bvgeom::db_box $stream $alias $box I-[escape_hex "[$inst getName]/[[$term getMTerm] getName]"] [$inst getTransform]
          }
        }
      }
    }
  }
  close $stream
  odb::delete_dbWirePathShape $element
  odb::delete_dbWirePath $path
  odb::delete_dbWirePathItr $itr
}
