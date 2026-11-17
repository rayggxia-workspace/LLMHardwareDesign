# Actual S/E via cut OBS, source bound in c-leaf-cut-source-binding.json.
set db [ord::get_db]
set tech [ord::get_db_tech]
set block [ord::get_db_block]
if {[$block getDbUnitsPerMicron]!=2000} {error "Unexpected source-cut DBU"}
set f [open /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/c-leaf-cut-obs.tsv]
set cuts [dict create];set added 0
while {[gets $f row]>=0} {
 lassign [split $row "\t"] master layer l b r t
 set m [$db findMaster $master];set ly [$tech findLayer $layer]
 if {$m eq "NULL" || $ly eq "NULL"} {error "Missing bound cut master/layer"}
 set exists 0
 foreach x [$m getObstructions] {
  if {[[$x getTechLayer] getName] eq $layer && [$x xMin]==$l && [$x yMin]==$b && [$x xMax]==$r && [$x yMax]==$t} {set exists 1;break}
 }
 if {!$exists} {odb::dbBox_create $m $ly $l $b $r $t;incr added}
 dict lappend cuts $master [list $layer $l $b $r $t]
}
close $f
puts "ADDED_ACTUAL_LEAF_CUT_OBS $added"
# Same 1.5 um guard convention as the qualified C PG landing filter.
# Remove only complete redundant parent M7->M10 via stacks near actual cuts.
set guard 3000;set binsize 16000;set index [dict create]
foreach inst [$block getInsts] {
 set master [[$inst getMaster] getName]
 if {![dict exists $cuts $master]} {continue}
 if {[$inst getOrient] ne "R0" || [[$inst getMaster] getOrigin] ne {0 0}} {error "Cut projection requires reviewed R0/zero origin"}
 lassign [$inst getLocation] ox oy
 foreach cut [dict get $cuts $master] {
  lassign $cut layer l b r t
  set l [expr {$l+$ox-$guard}];set b [expr {$b+$oy-$guard}]
  set r [expr {$r+$ox+$guard}];set t [expr {$t+$oy+$guard}]
  for {set i [expr {$l/$binsize}]} {$i<=$r/$binsize} {incr i} {
   for {set j [expr {$b/$binsize}]} {$j<=$t/$binsize} {incr j} {dict lappend index [list $layer $i $j] [list $l $b $r $t [$inst getName]]}
  }
 }
}
set report [open actual-cut-pg-removed.tsv w]
puts $report "supply\tx_dbu\ty_dbu\tactual_cut_context"
foreach supply {VDD VSS} {
 set stacks [dict create];set hits [dict create]
 foreach sw [[$block findNet $supply] getSWires] {
  foreach box [$sw getWires] {
   if {![$box isVia]} {continue}
   set via [$box getTechVia];if {$via eq "NULL"} {set via [$box getBlockVia]}
   set levels {}
   foreach shape [$via getBoxes] {set lev [[$shape getTechLayer] getRoutingLevel];if {$lev} {lappend levels $lev}}
   set levels [lsort -integer -unique $levels]
   if {$levels ni {{7 8} {8 9} {9 10}}} {continue}
   set loc [$box getViaXY];lassign $loc x y
   dict lappend stacks $loc [list $levels $box]
   foreach shape [$via getBoxes] {
    set layer [[$shape getTechLayer] getName]
    if {$layer ni {via7 via8 via9}} {continue}
    set l [expr {[$shape xMin]+$x}];set b [expr {[$shape yMin]+$y}]
    set r [expr {[$shape xMax]+$x}];set t [expr {[$shape yMax]+$y}]
    for {set i [expr {$l/$binsize}]} {$i<=$r/$binsize} {incr i} {
     for {set j [expr {$b/$binsize}]} {$j<=$t/$binsize} {incr j} {
      set key [list $layer $i $j];if {![dict exists $index $key]} {continue}
      foreach obstacle [dict get $index $key] {
       lassign $obstacle ol ob or ot name
       if {$l<$or && $r>$ol && $b<$ot && $t>$ob} {dict set hits $loc [list $layer $name]}
      }
     }
    }
   }
  }
 }
 dict for {loc hit} $hits {
  set stack [dict get $stacks $loc]
  set levels [lsort [lmap item $stack {lindex $item 0}]]
  if {$levels ne {{7 8} {8 9} {9 10}}} {error "Cannot remove incomplete parent PG stack $loc"}
  puts $report "$supply\t[join $loc \t]\t$hit"
  foreach item $stack {odb::dbSBox_destroy [lindex $item 1]}
 }
 puts "ACTUAL_CUT_PG_FILTER $supply removed [dict size $hits] stacks"
}
close $report
foreach rail {VDD VSS} {add_global_connection -net $rail -inst_pattern .* -pin_pattern $rail [expr {$rail eq "VDD" ? "-power" : "-ground"}]}
global_connect
foreach rail {VDD VSS} {if {[check_power_grid -net $rail] ne "1"} {error "Actual-cut PG filter broke $rail"}}
