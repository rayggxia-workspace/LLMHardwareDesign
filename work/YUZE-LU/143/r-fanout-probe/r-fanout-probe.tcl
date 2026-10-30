set_thread_count 16
read_db {/public/home/yuzelu/project-circuit/llm_routing_analysis/worktrees/issue143-seven-block-v2-20261030/outputs/030/pnr/r/flow/results/nangate45/bv1_block_v1_r/base/3_3_place_gp.odb}
set b [ord::get_db_block]
set pitch [expr {128*[$b getDbUnitsPerMicron]}]
set f [open fanout.tsv w]
puts $f "net\titerms\tbterms\tdrivers\tloads\tgroups\tmax_bin"
foreach net [$b getNets] {
 if {[$net getSigType] in {POWER GROUND CLOCK}} {continue}
 set count [llength [$net getITerms]]
 if {$count<=2048} {continue}
 set drivers 0;set loads 0;set bins {}
 foreach term [$net getITerms] {
  if {[[$term getMTerm] getIoType] eq "OUTPUT"} {incr drivers;continue}
  incr loads
  lassign [[$term getInst] getLocation] x y
  set key [list [expr {$x/$pitch}] [expr {$y/$pitch}]]
  dict incr bins $key
 }
 set groups 0;set maxbin 0
 dict for {key n} $bins {
  incr groups [expr {($n+255)/256}]
  if {$n>$maxbin} {set maxbin $n}
 }
 puts $f "[$net getName]\t$count\t[llength [$net getBTerms]]\t$drivers\t$loads\t$groups\t$maxbin"
}
close $f
