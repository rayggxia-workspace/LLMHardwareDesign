set root /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu
set source $::env(U_SOURCE)
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
foreach hook $::env(U_COMBINED_HOOKS) {source $hook}
set m [[ord::get_db] findMaster BUF_X$::env(U_TARGET_DRIVE)]
if {$m eq "NULL"} {error "Missing target buffer master"}
set f [open targeted-cell-changes.tsv w]
foreach name {place17297 place17567} {
 set i [$block findInst $name]
 if {$i eq "NULL" || [[$i getMaster] getName] ne "BUF_X1"} {error "Diagnosed cap driver mismatch $name"}
 $i swapMaster [[ord::get_db] findMaster BUF_X4]
 puts $f "$name\tBUF_X1\tBUF_X4"
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
foreach spec {{datapath.n32 {s_rsp_data[46]} datapath.store n32_46} {datapath.store {req_data[114]} wire22300 store114} {datapath.store {req_data[116]} wire40491 store116} {datapath.store {req_data[118]} wire22297 store118} {datapath.store {req_data[124]} wire22294 store124} {datapath.store req_write wire22499 storewrite} {elementwise {in_data[101]} {legacy_e.e_in_data[101]$_SDFFCE_PN0P_} e101}} {
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
 set matches {}
 foreach candidate [$block getInsts] {
  if {[string map [list "\\" ""] [$candidate getName]] eq $driver} {lappend matches $candidate}
 }
 if {[llength $matches]!=1} {error "Driver lookup $driver"}
 set di [lindex $matches 0]
 set dp [$di getBBox]
 if {[[$di getMaster] isBlock]} {
  set out [$di findITerm {rsp_data[46]}]
  set geometries [$out getGeometries]
  if {[llength $geometries]<1} {error "Macro driver lacks actual geometry"}
  set dp [lindex [lindex $geometries end] 1]
 }
 set dx [expr {([$dp xMin]+[$dp xMax])/2.0}];set dy [expr {([$dp yMin]+[$dp yMax])/2.0}]
 set sx [expr {([$pin xMin]+[$pin xMax])/2.0}];set sy [expr {([$pin yMin]+[$pin yMax])/2.0}]
 set fraction $::env(U_REPEATER_FRACTION)
 split_sink $sink "i289_repeater_$suffix" [expr {$dx+($sx-$dx)*$fraction}] [expr {$dy+($sy-$dy)*$fraction}]
}
set matches {}
foreach i [$block getInsts] {
 if {[string map [list "\\" ""] [$i getName]] eq {controller.task_packet[89]$_DFFE_PN0P_}} {lappend matches $i}
}
if {[llength $matches]!=1} {error "Exact task_packet89 state lookup"}
set si [lindex $matches 0]
set sink [$si findITerm D]
set prev [$sink getNet]
$sink disconnect
lassign [$si getLocation] x y
for {set j 0} {$j<$::env(U_TARGET_HOLD_COUNT)} {incr j} {
 set name i289_guardant_hold89_$j
 set i [odb::dbInst_create $block [[ord::get_db] findMaster CLKBUF_X1] $name]
 $i setLocation $x $y
 $i setPlacementStatus PLACED
 set net [odb::dbNet_create $block ${name}_net]
 [$i findITerm A] connect $prev
 [$i findITerm Z] connect $net
 set prev $net
}
$sink connect $prev
close $f
write_db targeted-edit.odb
puts TARGETED_ELECTRICAL_EDIT_WRITTEN_RELOAD_STA_REQUIRED
