set_thread_count 8
read_db /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/runs/C-v35-unified-i8-h100-pnone/flow/results/nangate45/c-overlay-current/base/6_final.odb
set b [ord::get_db_block]
set f [open /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/C-v35-upper-patch-v2/macro-obs.tsv w]
foreach i [$b getInsts] {
 set m [$i getMaster]
 if {![$m isBlock]} {continue}
 if {[$i getOrient] ne "R0"} {error "Unreviewed macro transform"}
 lassign [$i getOrigin] ox oy
 foreach box [$m getObstructions] {
  set l [$box getTechLayer]
  if {$l eq "NULL" || [$l getName] ni {metal9 metal10 via9}} {continue}
  puts $f [join [list [$i getName] [$l getName] [expr {$ox+[$box xMin]}] [expr {$oy+[$box yMin]}] [expr {$ox+[$box xMax]}] [expr {$oy+[$box yMax]}]] "\t"]
 }
}
close $f
