set_thread_count 8
set root /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu
read_db $::env(C_STAGE_INPUT_ODB)
source $root/geometry.tcl
geometry_snapshot geometry-original.tsv
# Isolate hook scratch variables and helper procs; frozen hook source is unchanged.
set hook_index 0
if {[info exists ::env(C_STAGE_EXTRA_HOOKS)]} {
 foreach hook $::env(C_STAGE_EXTRA_HOOKS) {
  namespace eval ::i289_actual_hook_$hook_index [list source $hook]
  incr hook_index
 }
}
set b [ord::get_db_block]
proc receiver_location {sink} {
 set i [$sink getInst]
 if {![[$i getMaster] isBlock]} {return [$i getLocation]}
 if {[$i getOrient] ne "R0"} {error "Unreviewed macro receiver orientation"}
 set best -1;set point {}
 lassign [$i getOrigin] ox oy
 foreach mp [[$sink getMTerm] getMPins] {foreach box [$mp getGeometry] {
  set l [$box getTechLayer]
  if {$l eq "NULL"} {continue}
  set level [$l getRoutingLevel]
  if {$level>$best} {
   set best $level
   set point [list [expr {$ox+([$box xMin]+[$box xMax])/2}] [expr {$oy+([$box yMin]+[$box yMax])/2}]]
  }
 }}
 if {$best<1} {error "No physical macro input geometry"}
 lassign $point x y
 set box [$i getBBox];set halo 8000
 set sides [list [list [expr {$x-[$box xMin]}] left] [list [expr {[$box xMax]-$x}] right] [list [expr {$y-[$box yMin]}] bottom] [list [expr {[$box yMax]-$y}] top]]
 set side [lindex [lindex [lsort -integer -index 0 $sides] 0] 1]
 switch $side {
  left {set x [expr {[$box xMin]-$halo}]}
  right {set x [expr {[$box xMax]+$halo}]}
  bottom {set y [expr {[$box yMin]-$halo}]}
  top {set y [expr {[$box yMax]+$halo}]}
 }
 return [list $x $y]
}
proc actual_branch_delay {sink count prefix strong} {
 set b [ord::get_db_block]
 set prev [$sink getNet]
 if {$prev eq "NULL" || [$prev getSigType] in {POWER GROUND CLOCK}} {error "Not a data/reset branch: $prefix"}
 lassign [receiver_location $sink] x y
 $sink disconnect
 set total [expr {$count+$strong}]
 for {set j 0} {$j<$total} {incr j} {
  set name ${prefix}_$j
  if {[$b findInst $name] ne "NULL" || [$b findNet ${name}_net] ne "NULL"} {error "Duplicate ECO object"}
  set mname CLKBUF_X1
  if {$strong && $j==$count} {set mname BUF_X8}
  set m [[ord::get_db] findMaster $mname]
  if {$m eq "NULL"} {error "Missing physical master $mname"}
  set i [odb::dbInst_create $b $m $name]
  $i setLocation $x $y
  $i setPlacementStatus PLACED
  set n [odb::dbNet_create $b ${name}_net]
  [$i findITerm A] connect $prev
  [$i findITerm Z] connect $n
  set prev $n
 }
 $sink connect $prev
}

set plan [open $root/c-v27-electrical-plan.tsv];gets $plan header
set iso_log [open actual-isolation-plan.tsv w]
set serial 0
while {[gets $plan line]>=0} {
 lassign [split $line "\t"] name old term net strategy xy
 if {$strategy ne "isolate"} {continue}
 set driver_inst [$b findInst $name]
 if {$driver_inst eq "NULL"} {error "Actual source driver disappeared $name"}
 set current [[$driver_inst getMaster] getName]
 if {[regsub {_X[0-9]+$} $current {}] ne [regsub {_X[0-9]+$} $old {}]} {error "Unreviewed driver function family change $name"}
 set driver [$driver_inst findITerm $term]
 if {$driver eq "NULL" || [[$driver getMTerm] getIoType] ne "OUTPUT"} {error "Not an output driver"}
 set oldnet [$driver getNet]
 if {[$oldnet getName] ne $net || [$oldnet getSigType] ne "SIGNAL"} {error "Driver net scope changed $name"}
 set outputs 0
 foreach it [$oldnet getITerms] {if {[[$it getMTerm] getIoType] eq "OUTPUT"} {incr outputs}}
 if {$outputs!=1} {error "Unexpected multidriver electrical ECO"}
 foreach bt [$oldnet getBTerms] {if {[$bt getIoType] eq "INPUT"} {error "External source cannot be isolated by output ECO"}}
 set nm i289_actual_$::env(C_STAGE_TAG)_iso$serial
 if {[$b findInst $nm] ne "NULL" || [$b findNet ${nm}_source] ne "NULL"} {error "Duplicate isolation ECO"}
 set master [[ord::get_db] findMaster BUF_X$::env(C_STAGE_ISO_SIZE)]
 if {$master eq "NULL"} {error "Missing isolation buffer master"}
 set ins [odb::dbInst_create $b $master $nm]
 lassign [receiver_location $driver] x y
 if {![[$driver_inst getMaster] isBlock]} {set x [expr {$x+[[$driver_inst getMaster] getWidth]+380}]}
 $ins setLocation $x $y
 $ins setPlacementStatus PLACED
 set short [odb::dbNet_create $b ${nm}_source]
 $driver disconnect
 $driver connect $short
 [$ins findITerm A] connect $short
 [$ins findITerm Z] connect $oldnet
 puts $iso_log "$name\t$current\t$term\t$net\t$nm\tBUF_X$::env(C_STAGE_ISO_SIZE)\t$x $y"
 incr serial
}
close $plan;close $iso_log
if {$serial!=28} {error "Exact nonbuffer isolation scope changed"}
set fast {}
set ff [open $root/diagnostics/C-fast-hold-probe-v1/branch-plan.tsv];gets $ff header
while {[gets $ff line]>=0} {
 lassign [split $line "\t"] ep hs inst term budget samples status
 if {$status eq "sampled_common_with_budget"} {dict set fast $ep [list $inst $term $budget]}
}
close $ff
set branch_queue {};set branch_log [open actual-fast-branches.tsv w]
set margin [expr {double($::env(C_STAGE_HOLD_MARGIN_PS))/1000.0}]
set f [open $::env(C_STAGE_HOLD_PLAN)];gets $f header
set out [open actual-hold-plan.tsv w]
puts $out "instance\tterminal\tmin_slack\tmax_slack\trequested\tchosen\tstrong_last"
set cells 0;set branches 0;set clamped 0
while {[gets $f line]>=0} {
 lassign [split $line "\t"] endpoint iname term hs ss status
 if {$status ne "data"} {error "Unreviewed remaining hold endpoint $endpoint"}
 set i [$b findInst $iname]
 if {$i eq "NULL"} {error "Hold endpoint disappeared"}
 set sink [$i findITerm $term]
 if {$sink eq "NULL"} {error "Hold terminal disappeared"}
 if {[dict exists $fast $endpoint]} {
  lassign [dict get $fast $endpoint] fi ft fs
  set ii [$b findInst $fi]
  if {$ii eq "NULL"} {error "Fast branch instance disappeared"}
  set ss $fs;set sink [$ii findITerm $ft]
  if {$sink eq "NULL" || [[$sink getMTerm] getIoType] ne "INPUT"} {error "Fast branch is not a true input"}
  set iname $fi;set term $ft
  puts $branch_log "$endpoint\t$fi\t$ft\t$hs\t$fs\tsampled_not_exhaustive_pending_actual_STA"
 }
 set requested [expr {max(0,int(ceil((-$hs+$margin)/.020)))}]
 # Every branch ends with BUF_X8 to drive the actual endpoint connection.
 set available [expr {max(0,int(floor(($ss-.060-.040)/.040)))}]
 set chosen [expr {min($requested,$available)}]
 if {$chosen<$requested} {incr clamped}
 puts $out "$iname\t$term\t$hs\t$ss\t$requested\t$chosen\t1"
 if {$chosen>0} {
  set key [list $iname $term]
  if {![dict exists $branch_queue $key] || $chosen>[dict get $branch_queue $key]} {dict set branch_queue $key $chosen}
 }
}
close $f;close $out;close $branch_log
foreach key [dict keys $branch_queue] {
 lassign $key ni nt
 set sink [[$b findInst $ni] findITerm $nt]
 set chosen [dict get $branch_queue $key]
 actual_branch_delay $sink $chosen i289_actual_$::env(C_STAGE_TAG)_h$branches 1
 incr cells [expr {$chosen+1}];incr branches
}
if {$cells>10000} {error "Hold buffer budget unexpectedly exceeded"}
geometry_snapshot geometry-after-edit.tsv
exec cmp geometry-original.tsv geometry-after-edit.tsv
write_db edited.odb
write_def edited.def
write_verilog edited.v
puts "ACTUAL_ECO_EDITS isolation=$serial hold_branches=$branches hold_cells=$cells setup_clamped=$clamped"
puts NO_RESET_EDITS_AND_NO_TIMING_EXCEPTIONS_POSTROUTE_VALIDATION_REQUIRED
