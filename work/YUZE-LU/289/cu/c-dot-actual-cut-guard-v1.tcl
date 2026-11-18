# Actual GDS cut geometry only; no pin, cell placement, or physical rule changes.
set dot_tsv /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/C-final-v1/macro-obs-v20/dot-actual-cut-obs.tsv
set dot_expected_sha 608f06d6a8b3956d590733be0a51b935435adce160f17754647c6207ffb2e872
if {[lindex [exec sha256sum $dot_tsv] 0] ne $dot_expected_sha} {error "Dot cut source binding changed"}
set dot_db [ord::get_db]
set dot_tech [$dot_db getTech]
set dot_master [$dot_db findMaster e_s32_pipeline_128]
if {$dot_master eq "NULL"} {error "Missing dot master"}
if {[$dot_master getOrigin] ne {0 0} || [$dot_master getWidth] != 920000 || [$dot_master getHeight] != 800000} {error "Unexpected dot master geometry"}
set dot_existing {}
foreach box [$dot_master getObstructions] {
 set layer [$box getTechLayer]
 if {$layer ne "NULL"} {dict set dot_existing [list [$layer getName] [$box xMin] [$box yMin] [$box xMax] [$box yMax]] 1}
}
set dot_rows {};set dot_counts {}
set dot_f [open $dot_tsv]
while {[gets $dot_f line] >= 0} {
 if {[string trim $line] eq ""} {continue}
 lassign $line name layer x1 y1 x2 y2
 if {$name ne "e_s32_pipeline_128" || $layer ni {via6 via7 via8 via9}} {error "Unexpected cut row: $line"}
 if {$x1<0 || $y1<0 || $x2>920000 || $y2>800000 || $x1 >= $x2 || $y1 >= $y2} {error "Invalid actual cut bounds"}
 if {[$dot_tech findLayer $layer] eq "NULL"} {error "Missing cut layer $layer"}
 lappend dot_rows [list $layer $x1 $y1 $x2 $y2]
 dict incr dot_counts $layer
}
close $dot_f
if {[llength $dot_rows] != 1970} {error "Expected 1970 actual cuts"}
foreach {layer count} {via6 1098 via7 298 via8 288 via9 286} {if {[dict get $dot_counts $layer] != $count} {error "Actual cut layer count mismatch"}}
set dot_added 0
foreach row $dot_rows {
 if {![dict exists $dot_existing $row]} {
  lassign $row layer x1 y1 x2 y2
  odb::dbBox_create $dot_master [$dot_tech findLayer $layer] $x1 $y1 $x2 $y2
  dict set dot_existing $row 1
  incr dot_added
 }
}
puts "ISSUE289_DOT_ACTUAL_CUT_OBS total1970 added$dot_added source_sha=$dot_expected_sha"