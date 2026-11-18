set root /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu
set source $root/runs/U-v8-postroute-h02-e10/flow/results/nangate45/u-overlay-current/base
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
foreach name {wire40497 wire40491 wire38369 wire40500 wire40492 wire40494 wire38339} {
 set i [$block findInst $name]
 if {$i eq "NULL"} {error "Missing diagnosed driver $name"}
 set old [[$i getMaster] getName]
 if {$old ni {BUF_X1 BUF_X4}} {error "Unexpected diagnosed driver type $name $old"}
 $i swapMaster $m
 if {[[$i getMaster] getName] ne "BUF_X$::env(U_TARGET_DRIVE)"} {error "Master swap failed"}
 puts $f "$name\t$old\t[[$i getMaster] getName]"
}
set hm [[ord::get_db] findMaster CLKBUF_X1]
foreach bit {120 110} {
 set count [expr {$bit==120 ? $::env(U_TARGET_HOLD_COUNT) : 1}]
  set target [format {datapath.held_score[%d]$_DFFE_PP_} $bit]
 set matches {}
 foreach candidate [$block getInsts] {
  set normalized [string map [list "\\" ""] [$candidate getName]]
  if {$normalized eq $target} {lappend matches $candidate}
 }
 if {[llength $matches] != 1} {error "Expected one exact normalized target $target; found [llength $matches]"}
 set si [lindex $matches 0]
 puts $f "HOLD_TARGET\t[$si getName]\t[[$si getMaster] getName]"
 if {$si eq "NULL"} {error "Missing diagnosed held_score $bit"}
 set sink [$si findITerm D]
 set prev [$sink getNet]
 $sink disconnect
 lassign [$si getLocation] x y
 for {set n 0} {$n<$count} {incr n} {
  set name "i289_target_hold_${bit}_$n"
  set bi [odb::dbInst_create $block $hm $name]
  $bi setLocation $x $y
  $bi setPlacementStatus PLACED
  set nn [odb::dbNet_create $block "${name}_net"]
  [$bi findITerm A] connect $prev
  [$bi findITerm Z] connect $nn
  set prev $nn
  puts $f "$name\tNEW\tCLKBUF_X1"
 }
 $sink connect $prev
}
close $f
write_db targeted-edit.odb
puts TARGETED_PURE_DB_EDIT_WRITTEN_RELOAD_STA_REQUIRED
