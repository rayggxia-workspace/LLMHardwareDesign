# Apply conservative routing keepouts only. Source after read_db; never edits physical metal.
set kg_pkg [file dirname [file normalize [info script]]]
source $kg_pkg/binding.tcl
set kg_db [ord::get_db]
set kg_tech [$kg_db getTech]
if {[$kg_tech getDbUnitsPerMicron]!=2000} {error "Unexpected DBU"}
foreach {file sha} $kg_hashes {if {[lindex [exec sha256sum $kg_pkg/$file] 0] ne $sha} {error "Keepout source hash changed $file"}}
set kg_f [open $kg_pkg/master-geometry.tsv]
set kg_expected_pins {};set kg_actual_pins {};set kg_existing {};set kg_masters {}
while {[gets $kg_f line]>=0} {
set a [split $line "\t"]
if {[lindex $a 0] eq "MASTER"} {
 lassign $a kind name width height
 set m [$kg_db findMaster $name]
 if {$m eq "NULL" || [$m getWidth]!=$width || [$m getHeight]!=$height || [$m getOrigin] ne {0 0}} {error "Master geometry mismatch $name"}
 dict set kg_masters $name $m
} elseif {[lindex $a 0] eq "PIN"} {lappend kg_expected_pins $a}
}
close $kg_f
foreach name [dict keys $kg_masters] {
set m [dict get $kg_masters $name]
foreach mt [$m getMTerms] {foreach mp [$mt getMPins] {foreach b [$mp getGeometry] {
set layer [[$b getTechLayer] getName]
if {$layer in {metal7 metal8 metal9 metal10 via7 via8 via9}} {lappend kg_actual_pins [list PIN $name $layer [$b xMin] [$b yMin] [$b xMax] [$b yMax] [$mt getName]]}
}}}
foreach b [$m getObstructions] {dict set kg_existing [list $name [[$b getTechLayer] getName] [$b xMin] [$b yMin] [$b xMax] [$b yMax]] 1}
}
if {[lsort $kg_actual_pins] ne [lsort $kg_expected_pins]} {error "Actual macro pins changed"}
set kg_f [open $kg_pkg/keepout.tsv];set kg_rows {}
while {[gets $kg_f line]>=0} {
 if {[string trim $line] eq ""} {continue}
 lassign $line name layer x1 y1 x2 y2
 if {![dict exists $kg_masters $name] || $layer ni {metal9 metal10 via9}} {error "Unexpected keepout"}
 set m [dict get $kg_masters $name]
 if {$x1<0 || $y1<0 || $x2>[$m getWidth] || $y2>[$m getHeight] || $x1>=$x2 || $y1>=$y2} {error "Keepout bounds"}
 foreach p $kg_actual_pins {
  lassign $p k pn pl a b c d
  if {$pn eq $name && $pl eq $layer && $x1<$c && $x2>$a && $y1<$d && $y2>$b} {error "Keepout intersects actual macro pin"}
 }
 lappend kg_rows [list $name $layer $x1 $y1 $x2 $y2]
}
close $kg_f
if {[llength $kg_rows]!=$kg_expected_count} {error "Keepout count changed"}
set kg_added 0
foreach row $kg_rows {
 if {[dict exists $kg_existing $row]} {continue}
 lassign $row name layer x1 y1 x2 y2
 odb::dbBox_create [dict get $kg_masters $name] [$kg_tech findLayer $layer] $x1 $y1 $x2 $y2
 dict set kg_existing $row 1
 incr kg_added
}
puts "C_ACTUAL_LOCAL_SPACING_KEEPOUT rows=[llength $kg_rows] added=$kg_added"
