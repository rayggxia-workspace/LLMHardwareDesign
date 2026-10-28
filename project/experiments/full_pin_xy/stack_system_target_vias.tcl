# Controlled native detailed-routing ECO, using only actual original via objects.
set b [ord::get_db_block];set tech [ord::get_db_tech]
set n [$b findNet {_215139_}]
if {$n eq "NULL" || [$n getSigType] ne "SIGNAL" || [llength [$n getBTerms]] || [llength [$n getITerms]]!=2} {error "Unexpected actual target net"}
if {[$n getNonDefaultRule] ne "NULL"} {error "Original target has NDR: explicit matching implementation required"}
set driver {};set sink {}
foreach it [$n getITerms] {
  set name "[[$it getInst] getName]/[[$it getMTerm] getName]"
  if {[$it getIoType] eq "OUTPUT" && $name eq "_562465_/ZN"} {set driver $it}
  if {[$it getIoType] eq "INPUT" && $name eq "_562527_/A2"} {set sink $it}
}
if {$driver eq "" || $sink eq ""} {error "Actual original driver/sink contract differs"}
proc m1_contains {it v x y {require_full_containment 1}} {
  set count 0
  foreach box [$v getBoxes] {
    if {[[$box getTechLayer] getName] ne "metal1"} {continue};incr count
    set a [expr {[$box xMin]+$x}];set c [expr {[$box yMin]+$y}];set d [expr {[$box xMax]+$x}];set e [expr {[$box yMax]+$y}];set fits 0
    foreach g [$it getGeometries] {
      if {[[lindex $g 0] getName] ne "metal1"} {continue};set r [lindex $g 1]
      if {[$r xMin]<=$a && [$r yMin]<=$c && [$r xMax]>=$d && [$r yMax]>=$e} {set fits 1}
      if {!$require_full_containment && [$r xMin]<$d && [$r yMin]<$e && [$r xMax]>$a && [$r yMax]>$c} {set fits 1}
    }
    if {!$fits} {return 0}
  }
  return [expr {$count>0}]
}
proc add_original_via {enc row} {
  lassign $row kind via x y
  if {$kind eq "TECH"} {$enc addTechVia $via} else {$enc addVia $via}
}
set w [$n getWire];if {$w eq "NULL"} {error "Original actual route missing"}
set itr [odb::dbWirePathItr];set path [odb::dbWirePath];set ps [odb::dbWirePathShape]
set via1 {};set via2 {};set f [open $out/original_actual_via_definitions.tsv w]
puts $f "via_name\tkind\tx_dbu\ty_dbu\tlayer\tx0_relative\ty0_relative\tx1_relative\ty1_relative"
$itr begin $w
while {[$itr getNextPath $path]} {while {[$itr getNextShape $ps]} {
  set s [odb::dbWirePathShape_shape_get $ps];if {![$s isVia]} {continue}
  set kind TECH;set v [$s getTechVia];if {$v eq "NULL"} {set kind BLOCK;set v [$s getVia]};lassign [$s getViaXY] x y
  set layers {}
  foreach box [$v getBoxes] {
    set layer [[$box getTechLayer] getName];lappend layers $layer
    puts $f [join [list [$v getName] $kind $x $y $layer [$box xMin] [$box yMin] [$box xMax] [$box yMax]] "\t"]
  }
  if {"metal1" in $layers && "metal2" in $layers} {lappend via1 [list $kind $v $x $y]}
  if {"metal2" in $layers && "metal3" in $layers} {lappend via2 [list $kind $v $x $y]}
}};close $f
if {[llength $via1]!=2 || [llength $via2]!=2} {error "Source is not the expected actual two via1/two via2 route"}
set sv1 {};set dv1 {}
foreach row $via1 {
  lassign $row kind v x y
  if {[m1_contains $sink $v $x $y 0]} {if {$sv1 ne ""} {error "Ambiguous sink via1"};set sv1 $row}
  if {[m1_contains $driver $v $x $y 0]} {if {$dv1 ne ""} {error "Ambiguous driver via1"};set dv1 $row}
}
if {$sv1 eq "" || $dv1 eq "" || $sv1 eq $dv1} {error "Original via1 cannot be assigned to actual M1 terminals"}
proc nearest_via2 {via1 via2} {
  lassign $via1 kind v x y;set best {};set score 1e100
  foreach row $via2 {lassign $row k vi xx yy;set d [expr {abs($x-$xx)+abs($y-$yy)}];if {$d<$score} {set score $d;set best $row}}
  return $best
}
set sv2 [nearest_via2 $sv1 $via2];set dv2 [nearest_via2 $dv1 $via2]
if {$sv2 eq $dv2} {error "Ambiguous source via2 pairing"}
lassign $sv1 ignored sv sx sy;lassign $dv1 ignored dv dx dy
# Use the original driver's actual track Y; both new M1 via landings must fit
# wholly inside the unchanged actual corresponding terminal rectangles.
set common_y $dy
if {![m1_contains $sink $sv $sx $common_y] || ![m1_contains $driver $dv $dx $common_y]} {error "Proposed actual via1 landings escape original M1 terminals"}
set f [open $out/actual_detail_edit.json w]
puts $f [format {{"target_net":"_215139_","driver":"_562465_/ZN","sink":"_562527_/A2","source_sink_via1_xy_dbu":[%d,%d],"source_driver_via1_xy_dbu":[%d,%d],"new_sink_stack_xy_dbu":[%d,%d],"new_driver_stack_xy_dbu":[%d,%d],"all_via_definitions_reused_from_original_actual_net":true,"all_new_M1_via_landings_contained_in_unchanged_actual_ITerms":true,"DBU_per_um":%d}} $sx $sy $dx $dy $sx $common_y $dx $common_y [$b getDbUnitsPerMicron]];close $f
odb::dbWire_destroy $w
set w [odb::dbWire_create $n];set enc [odb::dbWireEncoder];$enc begin $w
$enc newPath [$tech findLayer metal1] ROUTED
$enc addPoint $sx $common_y;add_original_via $enc $sv1;add_original_via $enc $sv2
$enc addPoint $dx $common_y;add_original_via $enc $dv2;add_original_via $enc $dv1
$enc end
puts "ACTUAL_STACKED_VIA_NATIVE_DETAIL_EDIT_REQUIRES_FRESH_DRC_WHOLE_CONNECTIVITY_RCX_STA"
