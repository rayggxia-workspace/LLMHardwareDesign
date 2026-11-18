read_db /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/runs/C-v18-donly-m0.04-d0.025/flow/results/nangate45/c-overlay-current/base/4_cts.odb
set seen [dict create]
foreach i [[ord::get_db_block] getInsts] {
 set m [$i getMaster]
 if {![$m isBlock] || [dict exists $seen [$m getName]]} {continue}
 dict set seen [$m getName] 1
 set area [expr {double([$m getWidth])*[$m getHeight]}]
 set box [$i getBBox]
 puts "MACRO [$i getName] [$m getName] [$box xMin] [$box yMin] [$box xMax] [$box yMax]"
 foreach lname {metal7 metal8 metal9 metal10} {
  set n 0;set biggest 0;set sum 0
  foreach obs [$m getObstructions] {
   if {[[$obs getTechLayer] getName] ne $lname} {continue}
   incr n
   set a [expr {double([$obs xMax]-[$obs xMin])*([$obs yMax]-[$obs yMin])}]
   set biggest [expr {max($biggest,$a)}];set sum [expr {$sum+$a}]
  }
  puts "OBS $lname count=$n biggest_ratio=[expr {$biggest/$area}] raw_sum_ratio=[expr {$sum/$area}]"
 }
}