# Adapted from existing H1 filter_pg.tcl; only newly generated parent PG vias may be removed.
# Extended for actual M10 macro OBS. All original macro geometry remains immutable.
# 2um is a conservative PG landing guard on actual M7-M10 layers (each table max1.5um).
# This is not a signal-pin rule or complete DRC/PDN qualification.
proc llhd_filter_macro {llhd_instance_name} {
set llhd_check_only [expr {[info exists ::env(PINXY_PG_AUDIT_MODE)] && $::env(PINXY_PG_AUDIT_MODE) == 2}]
set llhd_block [ord::get_db_block]
set llhd_inst [$llhd_block findInst $llhd_instance_name]
if { $llhd_inst == "NULL" || [$llhd_inst getOrient] != "R0" } {
  error "PG access selection requires the specified macro at R0"
}
set llhd_scale [expr {round(1.0 / [ord::dbu_to_microns 1])}]
lassign [$llhd_inst getLocation] llhd_ox llhd_oy
set llhd_master [$llhd_inst getMaster]
lassign [$llhd_master getOrigin] llhd_mx llhd_my
if { $llhd_mx != 0 || $llhd_my != 0 } { error "Nonzero master origin needs a reviewed transform" }
set llhd_bbox [$llhd_inst getBBox]
set llhd_bbox_coords [list [$llhd_bbox xMin] [$llhd_bbox yMin] [$llhd_bbox xMax] [$llhd_bbox yMax]]
set llhd_guard [expr {2*$llhd_scale}]
set llhd_obs [dict create metal7 {} metal8 {} metal9 {} metal10 {}]
set llhd_obs_count 0
foreach box [$llhd_master getObstructions] {
  incr llhd_obs_count
  set layer [[$box getTechLayer] getName]
  if { ![dict exists $llhd_obs $layer] } { continue }
  dict lappend llhd_obs $layer [list \
    [expr {[$box xMin]+$llhd_ox}] [expr {[$box yMin]+$llhd_oy}] \
    [expr {[$box xMax]+$llhd_ox}] [expr {[$box yMax]+$llhd_oy}]]
}
# Empty upper layers are legitimate for the M8-limited SYSTEM blocks.
set llhd_pg_pins [dict create VDD {} VSS {}]
foreach supply {VDD VSS} {
  set term [$llhd_master findMTerm $supply]
  if { $term == "NULL" } { error "Missing $supply master pin" }
  foreach pin [$term getMPins] {
    foreach box [$pin getGeometry] {
      if { [[$box getTechLayer] getName] != "metal7" } { error "Unexpected PG pin layer" }
      dict lappend llhd_pg_pins $supply [list \
        [expr {[$box xMin]+$llhd_ox}] [expr {[$box yMin]+$llhd_oy}] \
        [expr {[$box xMax]+$llhd_ox}] [expr {[$box yMax]+$llhd_oy}]]
    }
  }
}
set file [open $::env(PINXY_PARENT_OUT)/${llhd_instance_name}-pg-access-obstructions.tsv w]
puts $file "layer\txmin_dbu\tymin_dbu\txmax_dbu\tymax_dbu\tguard_dbu"
foreach layer {metal7 metal8 metal9 metal10} {
  foreach rect [dict get $llhd_obs $layer] { puts $file "$layer\t[join $rect \t]\t$llhd_guard" }
}
close $file
set file [open $::env(PINXY_PARENT_OUT)/${llhd_instance_name}-pg-access-pins.tsv w]
puts $file "net\txmin_dbu\tymin_dbu\txmax_dbu\tymax_dbu"
foreach supply {VDD VSS} {
  foreach rect [dict get $llhd_pg_pins $supply] { puts $file "$supply\t[join $rect \t]" }
}
close $file

proc llhd_via_rows {box} {
  set via [$box getTechVia]
  if { $via == "NULL" } { set via [$box getBlockVia] }
  if { $via == "NULL" } { error "Unresolved PG via master" }
  lassign [$box getViaXY] x y
  set rows {}
  foreach shape [$via getBoxes] {
    set layer [$shape getTechLayer]
    if { [$layer getRoutingLevel] == 0 } { continue }
    lappend rows [list [$via getName] [$layer getName] \
      [expr {[$shape xMin]+$x}] [expr {[$shape yMin]+$y}] \
      [expr {[$shape xMax]+$x}] [expr {[$shape yMax]+$y}]]
  }
  return $rows
}
proc llhd_pg_collisions {supply rows llhd_obs llhd_pg_pins llhd_guard} {
  set hits {}
  foreach row $rows {
    lassign $row via layer lx ly ux uy
    if { $layer ni {metal7 metal8 metal9 metal10} } { continue }
    if { $layer == "metal7" } {
      set contained 0
      foreach pin [dict get $llhd_pg_pins $supply] {
        lassign $pin px py qx qy
        if { $lx >= $px && $ly >= $py && $ux <= $qx && $uy <= $qy } { set contained 1; break }
      }
      # Existing same-net M7 PG shapes are a deliberate, fully contained contact.
      if { $contained } { continue }
    }
    foreach obs [dict get $llhd_obs $layer] {
      lassign $obs px py qx qy
      if { $lx-$llhd_guard < $qx && $ux+$llhd_guard > $px && \
           $ly-$llhd_guard < $qy && $uy+$llhd_guard > $py } {
        lappend hits [list {*}$row {*}$obs]
      }
    }
  }
  return $hits
}

# Only the newly generated parent's special-wire vias are selected here.
set llhd_groups [dict create]
set llhd_rows [dict create]
set llhd_edges [dict create]
set llhd_vias_before 0
foreach supply {VDD VSS} {
  set net [$llhd_block findNet $supply]
  if { $net == "NULL" } { error "Missing parent supply net" }
  foreach wire [$net getSWires] {
    foreach box [$wire getWires] {
      if { ![$box isVia] } {
        if { [[$box getTechLayer] getName] in {metal8 metal9} } {
          error "Unexpected independent M8/M9 PG patch: policy supports via stacks only"
        }
        continue
      }
      incr llhd_vias_before
      lassign [$box getViaXY] x y
      set key [list $supply $x $y]
      dict lappend llhd_groups $key $box
      set rows [llhd_via_rows $box]
      foreach row $rows { dict lappend llhd_rows $key $row }
      set levels {}
      foreach row $rows {
        regexp {^metal([0-9]+)$} [lindex $row 1] ignored level
        lappend levels $level
      }
      set levels [lsort -integer -unique $levels]
      if { 8 in $levels || 9 in $levels } { dict lappend llhd_edges $key [join $levels -] }
    }
  }
}
set file [open $::env(PINXY_PARENT_OUT)/${llhd_instance_name}-pg-removed-sites.tsv w]
puts $file "net\tx_dbu\ty_dbu\tvia_master\tlayer\tlanding_xmin\tlanding_ymin\tlanding_xmax\tlanding_ymax\tobs_xmin\tobs_ymin\tobs_xmax\tobs_ymax\tguard_dbu"
set llhd_unsafe_sites 0
set llhd_removed_sites 0
set llhd_removed_vias 0
dict for {key boxes} $llhd_groups {
  lassign $key supply x y
  if { [dict exists $llhd_edges $key] && [lsort [dict get $llhd_edges $key]] ne {7-8 8-9 9-10} } {
    error "Unexpected incomplete/nonadjacent PG stack at $key"
  }
  set hits [llhd_pg_collisions $supply [dict get $llhd_rows $key] $llhd_obs $llhd_pg_pins $llhd_guard]
  if { [llength $hits] == 0 } { continue }
  foreach hit $hits { puts $file "$supply\t$x\t$y\t[join $hit \t]\t$llhd_guard" }
  incr llhd_unsafe_sites
  if { $llhd_check_only } { continue }
  incr llhd_removed_sites
  foreach box $boxes { odb::dbSBox_destroy $box; incr llhd_removed_vias }
}
close $file

# Fresh enumeration after mutation; independently exported for a reviewer.
set file [open $::env(PINXY_PARENT_OUT)/${llhd_instance_name}-pg-retained-landings.tsv w]
puts $file "net\tx_dbu\ty_dbu\tvia_master\tlayer\txmin_dbu\tymin_dbu\txmax_dbu\tymax_dbu"
set llhd_vias_after 0
set llhd_remaining_hits 0
foreach supply {VDD VSS} {
  foreach wire [[$llhd_block findNet $supply] getSWires] {
    foreach box [$wire getWires] {
      if { ![$box isVia] } { continue }
      incr llhd_vias_after
      lassign [$box getViaXY] x y
      set rows [llhd_via_rows $box]
      incr llhd_remaining_hits [llength [llhd_pg_collisions $supply $rows $llhd_obs $llhd_pg_pins $llhd_guard]]
      foreach row $rows { puts $file "$supply\t$x\t$y\t[join $row \t]" }
    }
  }
}
close $file
set file [open $::env(PINXY_PARENT_OUT)/${llhd_instance_name}-pg-access-selection.json w]
puts $file "\{"
puts $file "  \"check_only\": [expr {$llhd_check_only ? {true} : {false}}],"
puts $file "  \"master\": \"[$llhd_master getName]\","
puts $file "  \"orientation\": \"[$llhd_inst getOrient]\","
puts $file "  \"instance_location_dbu\": \[$llhd_ox, $llhd_oy\],"
puts $file "  \"instance_bbox_dbu\": \[[join $llhd_bbox_coords {, }]\],"
puts $file "  \"coordinate_contract\": \"Actual master origin 0 0 asserted; actual R0 location and bbox recorded here.\","
puts $file "  \"dbu_per_micron\": $llhd_scale,"
puts $file "  \"guard_um\": 2.0,"
puts $file "  \"guard_basis\": \"Fixed-image Nangate45 individually verified M7/M8/M9/M10 SPACINGTABLE maxima 1.5um; 2um conservative landing guard. Not complete spacing signoff.\","
puts $file "  \"actual_master_obstruction_count\": $llhd_obs_count,"
puts $file "  \"M10_macro_obstructions\": [llength [dict get $llhd_obs metal10]],"
puts $file "  \"parent_pg_vias_before\": $llhd_vias_before,"
puts $file "  \"unsafe_same_net_xy_groups\": $llhd_unsafe_sites,"
puts $file "  \"removed_same_net_xy_groups\": $llhd_removed_sites,"
puts $file "  \"removed_parent_pg_vias\": $llhd_removed_vias,"
puts $file "  \"parent_pg_vias_after\": $llhd_vias_after,"
puts $file "  \"remaining_guard_intersections\": $llhd_remaining_hits,"
puts $file "  \"scope\": \"All new parent PG via groups (including lower-parent vias); actual imported M7/M8/M9/M10 OBS on every actual landing layer with full guard; M7 fully contained same-net PG contact allowed, otherwise guarded OBS. M10 macro OBS explicitly checked, including native M10 signal shapes. All retained landings exported; strict PG/native and final PSM remain required.\""
puts $file "\}"
close $file
if { $llhd_vias_before-$llhd_removed_vias != $llhd_vias_after || $llhd_remaining_hits != 0 } {
  error "PG site selection failed its fresh-enumeration invariant"
}
puts "PG ACCESS SELECTION removed $llhd_removed_vias vias at $llhd_removed_sites sites; retained $llhd_vias_after vias"
}
foreach llhd_instance_name $llhd_macro_instances {llhd_filter_macro $llhd_instance_name}
