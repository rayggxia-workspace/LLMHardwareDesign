set root /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu
set source $root/runs/U-v11-targeted-n4-x8/flow/results/nangate45/u-overlay-current/base
read_db $source/6_final.odb
set block [ord::get_db_block]
source $root/geometry.tcl
geometry_snapshot $::env(U_RESULTS)/geometry-before.tsv
proc net_signature {net} {
 set result {}
 foreach it [$net getITerms] {set i [$it getInst];lappend result [list [$i getName] [[$i getMaster] getName] [$i getLocation] [$i getOrient] [[$it getMTerm] getName]]}
 foreach b [$net getBTerms] {lappend result [list BTERM [$b getName]]}
 return [lsort $result]
}
set original [dict create]
foreach n [$block getNets] {dict set original [$n getName] [net_signature $n]}
set f [open original-net-signatures.tcllist w];puts $f [list $original];close $f
set m [[ord::get_db] findMaster BUF_X$::env(U_TARGET_DRIVE)]
if {$m eq "NULL"} {error "Missing target buffer master"}
set f [open targeted-cell-changes.tsv w]
foreach name {wire40495 wire40496 wire40498 wire40499 wire40501 wire40502 wire40503 wire40504 wire40505 wire40506 wire40507 wire40508 wire40510} {
 set i [$block findInst $name]
 if {$i eq "NULL"} {error "Missing diagnosed driver $name"}
 set old [[$i getMaster] getName]
 if {$old ni {BUF_X1 BUF_X4}} {error "Unexpected diagnosed driver type $name $old"}
 $i swapMaster $m
 if {[[$i getMaster] getName] ne "BUF_X$::env(U_TARGET_DRIVE)"} {error "Master swap failed"}
 puts $f "$name\t$old\t[[$i getMaster] getName]"
}
proc safe_location {x y} {
 set b [ord::get_db_block]
 set die [$b getDieArea]
 set pad 34000
 set x [expr {max([$die xMin]+$pad,min([$die xMax]-$pad,$x))}]
 set y [expr {max([$die yMin]+$pad,min([$die yMax]-$pad,$y))}]
 for {set attempt 0} {$attempt<12} {incr attempt} {
  set changed 0
  foreach i [$b getInsts] {
   if {![[$i getMaster] isBlock]} {continue}
   set box [$i getBBox];set halo 8000
   set l [expr {[$box xMin]-$halo}];set r [expr {[$box xMax]+$halo}]
   set bot [expr {[$box yMin]-$halo}];set top [expr {[$box yMax]+$halo}]
   if {$x>$l && $x<$r && $y>$bot && $y<$top} {
    set options [list [list [expr {$x-$l}] $l $y] [list [expr {$r-$x}] $r $y] [list [expr {$y-$bot}] $x $bot] [list [expr {$top-$y}] $x $top]]
    lassign [lindex [lsort -real -index 0 $options] 0] distance x y
    set changed 1
   }
  }
  if {!$changed} {return [list [expr {int($x)}] [expr {int($y)}]]}
 }
 error "Cannot find clear buffer placement seed"
}
proc split_sink {sink name x y} {
 set b [ord::get_db_block]
 set old [$sink getNet]
 if {$old eq "NULL"} {error "Unconnected sink"}
 set master [[ord::get_db] findMaster BUF_X8]
 set bi [odb::dbInst_create $b $master $name]
 lassign [safe_location $x $y] x y
 $bi setLocation $x $y
 $bi setPlacementStatus PLACED
 set nn [odb::dbNet_create $b "${name}_net"]
 $sink disconnect
 $sink connect $nn
 [$bi findITerm A] connect $old
 [$bi findITerm Z] connect $nn
 puts "SPLIT_SINK $name x=$x y=$y original_net=[$old getName]"
}
set bt [$block findBTerm {incoming_data[53]}]
set boxes {}
foreach bp [$bt getBPins] {foreach box [$bp getBoxes] {lappend boxes $box}}
if {[llength $boxes]!=1} {error "Expected one incoming_data53 BPin box"}
set box [lindex $boxes 0]
set x [expr {([$box xMin]+[$box xMax])/2}];set y [expr {([$box yMin]+[$box yMax])/2}]
set iso_sink [[$block findInst wire39017] findITerm A]
if {[$iso_sink getNet] ne [$bt getNet]} {error "Input53 diagnosed topology changed"}
split_sink $iso_sink i289_input53_isolation $x $y
foreach spec {{datapath.n32 {s_rsp_data[39]} wire40497 n32_39} {datapath.store {req_data[60]} wire38369 store60}} {
 lassign $spec macro term driver suffix
 set mi [$block findInst $macro]
 set sink [$mi findITerm $term]
 if {$sink eq "NULL"} {
  set matches {}
  foreach it [$mi getITerms] {if {[string map [list "\\" ""] [[$it getMTerm] getName]] eq $term} {lappend matches $it}}
  if {[llength $matches]!=1} {error "Expected exact macro sink $term"}
  set sink [lindex $matches 0]
 }
  set pins {};set maxlevel 0
 foreach geom [$sink getGeometries] {
  lassign $geom layer rect
  set level [$layer getRoutingLevel]
  if {$level>$maxlevel} {set maxlevel $level;set pins {}}
  if {$level==$maxlevel && $level>0} {lappend pins $rect}
 }
 if {[llength $pins]<1} {error "No actual routing-metal geometry for $macro/$term"}
 puts "REPEATER_ACTUAL_PIN $macro/$term highest_routing_level=$maxlevel shapes=[llength $pins]"
 set pin [lindex $pins 0]
 set dp [[$block findInst $driver] getBBox]
 set dx [expr {([$dp xMin]+[$dp xMax])/2.0}];set dy [expr {([$dp yMin]+[$dp yMax])/2.0}]
 set sx [expr {([$pin xMin]+[$pin xMax])/2.0}];set sy [expr {([$pin yMin]+[$pin yMax])/2.0}]
 set fraction $::env(U_REPEATER_FRACTION)
 split_sink $sink "i289_repeater_$suffix" [expr {$dx+($sx-$dx)*$fraction}] [expr {$dy+($sy-$dy)*$fraction}]
}
close $f
write_db targeted-edit.odb
puts TARGETED_ELECTRICAL_EDIT_WRITTEN_RELOAD_STA_REQUIRED
