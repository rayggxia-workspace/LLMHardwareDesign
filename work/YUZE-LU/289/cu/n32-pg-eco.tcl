set root /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu
read_db $root/runs/U-v6-ctsdelay-x8-seed0/flow/results/nangate45/u-overlay-current/base/5_1_grt.odb
set b [ord::get_db_block]
set tech [[ord::get_db] getTech]
set pinboxes {}
foreach it [[$b findInst datapath.n32] getITerms] {
 if {[[$it getMTerm] getSigType] in {POWER GROUND}} {continue}
 foreach g [$it getGeometries] {lassign $g l r;if {[$l getName] eq "metal6" && [$r yMin]==1996280} {lappend pinboxes [list [$r xMin] [$r xMax]]}}
}
set via [$tech findVia via6_0]
if {$via eq "NULL"} {error "Required real via6_0 missing"}
set edits 0
set log [open $root/n32-pg-eco.tsv w]
foreach sw [[$b findNet VDD] getSWires] {
 set stripes {}
 foreach r [$sw getWires] {
  if {[$r isVia] || [[$r getTechLayer] getName] ne "metal6" || [$r yMax]!=1997400 || [$r yMin]!=1292720} {continue}
  set hit 0
  foreach p $pinboxes {lassign $p a c;if {[$r xMin]<$c && [$r xMax]>$a} {set hit 1;break}}
  if {$hit} {lappend stripes $r}
 }
 foreach r $stripes {
  set x0 [$r xMin];set x1 [$r xMax];set y0 [$r yMin]
  set cx [expr {($x0+$x1)/2}]
  set removals {}
  foreach v [$sw getWires] {
   if {![$v isVia]} {continue}
   set bv [$v getBlockVia]
   if {$bv eq "NULL" || ![string match via6_7_* [$bv getName]]} {continue}
   if {([$v xMin]+[$v xMax])/2==$cx && [$v yMin]==1994600 && [$v yMax]==1997400} {lappend removals $v}
  }
  if {[llength $removals]!=1} {error "Expected exactly one top PG via array at $cx"}
  odb::dbSBox_destroy $r
  foreach v $removals {odb::dbSBox_destroy $v}
  odb::dbSBox_create $sw [$tech findLayer metal6] $x0 $y0 $x1 1995900 STRIPE
  foreach dx {-600 0 600} {
   if {$cx+$dx-140<$x0 || $cx+$dx+140>$x1} {error "Replacement via enclosure outside retained PG stripe"}
   foreach cy {1995000 1995600} {odb::dbSBox_create $sw $via [expr {$cx+$dx}] $cy STRIPE}
  }
  puts $log "$cx\t$x0\t$x1\t1995900\t6-real-via6_0-cuts"
  incr edits
 }
}
close $log
if {$edits==0} {error "No exact conflicting PG stripes found"}
foreach rail {VDD VSS} {if {[check_power_grid -net $rail] ne "1"} {error "PG continuity failed after ECO: $rail"}}
write_db $root/n32-pg-eco.odb
puts "N32_PG_CANDIDATE_CONNECTED $edits; full DRC and routing still required"
