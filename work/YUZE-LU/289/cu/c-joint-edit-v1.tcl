set_thread_count 8
set root /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu
read_db electric.odb
set b [ord::get_db_block]
source $root/c-dot-actual-cut-guard-v1.tcl
source /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/C-antenna-main-v2/hook.tcl
if {[info exists ::env(C_EXTRA_HOOKS)]} {foreach hook $::env(C_EXTRA_HOOKS) {source $hook}}
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
proc add_data_delay {sink count prefix strong} {
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
set margin [expr {double($::env(C_ECO_HOLD_PS))/1000.0}]
set f [open $root/diagnostics/C-main-hold-budget-v3/hold-setup-budget.tsv]
gets $f header
set out [open actual-hold-plan.tsv w]
puts $out "instance\tterminal\tmin_slack\tmax_slack\trequested\tchosen\tstrong_last"
set serial 0;set cells 0;set clamped 0
while {[gets $f line]>=0} {
 lassign [split $line "\t"] endpoint iname term hs ss status
 if {$status ne "data"} {continue}
 set i [$b findInst $iname]
 if {$i eq "NULL"} {error "Data endpoint disappeared after electrical repair: $iname"}
 set sink [$i findITerm $term]
 if {$sink eq "NULL"} {error "Data terminal disappeared: $iname/$term"}
 set strong [expr {[[$i getMaster] isBlock] ? 1 : 0}]
 set requested [expr {int(ceil((-$hs+$margin)/.020))}]
 set available [expr {max(0,int(floor(($ss-.050-.040*$strong)/.040)))}]
 set chosen [expr {min($requested,$available)}]
 if {$chosen<$requested} {incr clamped}
 puts $out "$iname\t$term\t$hs\t$ss\t$requested\t$chosen\t$strong"
 if {$chosen>0} {
  add_data_delay $sink $chosen i289_cjoint_$::env(C_ECO_TAG)_d$serial $strong
  incr cells [expr {$chosen+$strong}]
  incr serial
 }
}
close $f;close $out
if {$cells>10000} {error "Unexpectedly large targeted hold plan"}
set reset [$b findInst input1249]
if {$reset eq "NULL"} {error "Exact raw-reset branch missing"}
set resetcount [expr {max(3,int(ceil((.040+$margin)/.020)))}]
add_data_delay [$reset findITerm A] $resetcount i289_cjoint_$::env(C_ECO_TAG)_reset 0
puts "ACTUAL_TARGETED_HOLD branches=$serial cells=$cells clamped=$clamped resetcells=$resetcount"
write_db edited.odb
write_def edited.def
puts PURE_DB_JOINT_EDITS_REQUIRE_RELOAD_LEGALIZE_ROUTE_EXTRACT
