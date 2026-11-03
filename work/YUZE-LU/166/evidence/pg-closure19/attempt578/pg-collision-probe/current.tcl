set_thread_count 16
set f [open cells_current.tsv w]
read_db {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-166-r-local-state/attempt539/physical/flow/results/nangate45/r166_1024/base/6_final.odb}
set block [ord::get_db_block]
set dbu [$block getDbUnitsPerMicron]
set bounds [list 86.835 1116.375 88.905 1118.445]
foreach inst [$block getInsts] {
 set b [$inst getBBox];lassign $bounds x1 y1 x2 y2
 if {[$b xMin]>$x2*$dbu || [$b xMax]<$x1*$dbu || [$b yMin]>$y2*$dbu || [$b yMax]<$y1*$dbu} {continue}
 set group [$inst getGroup];if {$group ne "NULL"} {set group [$group getName]}
 puts $f [join [list current 0 [$inst getName] [[$inst getMaster] getName] [$inst getLocation] [$inst getOrient] [$inst getPlacementStatus] $group [$b xMin] [$b yMin] [$b xMax] [$b yMax]] "	"]
 foreach term [$inst getITerms] {
  if {[[$term getMTerm] getSigType] ni {POWER GROUND}} {continue}
  set net [$term getNet];if {$net ne "NULL"} {set net [$net getName]}
  puts $f [join [list PG [$inst getName] [[$term getMTerm] getName] $net] "	"]
 }
}
set bounds [list 87.405 1116.375 89.47 1118.445]
foreach inst [$block getInsts] {
 set b [$inst getBBox];lassign $bounds x1 y1 x2 y2
 if {[$b xMin]>$x2*$dbu || [$b xMax]<$x1*$dbu || [$b yMin]>$y2*$dbu || [$b yMax]<$y1*$dbu} {continue}
 set group [$inst getGroup];if {$group ne "NULL"} {set group [$group getName]}
 puts $f [join [list current 1 [$inst getName] [[$inst getMaster] getName] [$inst getLocation] [$inst getOrient] [$inst getPlacementStatus] $group [$b xMin] [$b yMin] [$b xMax] [$b yMax]] "	"]
 foreach term [$inst getITerms] {
  if {[[$term getMTerm] getSigType] ni {POWER GROUND}} {continue}
  set net [$term getNet];if {$net ne "NULL"} {set net [$net getName]}
  puts $f [join [list PG [$inst getName] [[$term getMTerm] getName] $net] "	"]
 }
}
set bounds [list 87.47 1116.375 89.475 1118.445]
foreach inst [$block getInsts] {
 set b [$inst getBBox];lassign $bounds x1 y1 x2 y2
 if {[$b xMin]>$x2*$dbu || [$b xMax]<$x1*$dbu || [$b yMin]>$y2*$dbu || [$b yMax]<$y1*$dbu} {continue}
 set group [$inst getGroup];if {$group ne "NULL"} {set group [$group getName]}
 puts $f [join [list current 2 [$inst getName] [[$inst getMaster] getName] [$inst getLocation] [$inst getOrient] [$inst getPlacementStatus] $group [$b xMin] [$b yMin] [$b xMax] [$b yMax]] "	"]
 foreach term [$inst getITerms] {
  if {[[$term getMTerm] getSigType] ni {POWER GROUND}} {continue}
  set net [$term getNet];if {$net ne "NULL"} {set net [$net getName]}
  puts $f [join [list PG [$inst getName] [[$term getMTerm] getName] $net] "	"]
 }
}
set bounds [list 159.035 1356.755 161.105 1358.825]
foreach inst [$block getInsts] {
 set b [$inst getBBox];lassign $bounds x1 y1 x2 y2
 if {[$b xMin]>$x2*$dbu || [$b xMax]<$x1*$dbu || [$b yMin]>$y2*$dbu || [$b yMax]<$y1*$dbu} {continue}
 set group [$inst getGroup];if {$group ne "NULL"} {set group [$group getName]}
 puts $f [join [list current 3 [$inst getName] [[$inst getMaster] getName] [$inst getLocation] [$inst getOrient] [$inst getPlacementStatus] $group [$b xMin] [$b yMin] [$b xMax] [$b yMax]] "	"]
 foreach term [$inst getITerms] {
  if {[[$term getMTerm] getSigType] ni {POWER GROUND}} {continue}
  set net [$term getNet];if {$net ne "NULL"} {set net [$net getName]}
  puts $f [join [list PG [$inst getName] [[$term getMTerm] getName] $net] "	"]
 }
}
set bounds [list 159.605 1356.755 161.67 1358.825]
foreach inst [$block getInsts] {
 set b [$inst getBBox];lassign $bounds x1 y1 x2 y2
 if {[$b xMin]>$x2*$dbu || [$b xMax]<$x1*$dbu || [$b yMin]>$y2*$dbu || [$b yMax]<$y1*$dbu} {continue}
 set group [$inst getGroup];if {$group ne "NULL"} {set group [$group getName]}
 puts $f [join [list current 4 [$inst getName] [[$inst getMaster] getName] [$inst getLocation] [$inst getOrient] [$inst getPlacementStatus] $group [$b xMin] [$b yMin] [$b xMax] [$b yMax]] "	"]
 foreach term [$inst getITerms] {
  if {[[$term getMTerm] getSigType] ni {POWER GROUND}} {continue}
  set net [$term getNet];if {$net ne "NULL"} {set net [$net getName]}
  puts $f [join [list PG [$inst getName] [[$term getMTerm] getName] $net] "	"]
 }
}
set bounds [list 159.67 1356.755 161.675 1358.825]
foreach inst [$block getInsts] {
 set b [$inst getBBox];lassign $bounds x1 y1 x2 y2
 if {[$b xMin]>$x2*$dbu || [$b xMax]<$x1*$dbu || [$b yMin]>$y2*$dbu || [$b yMax]<$y1*$dbu} {continue}
 set group [$inst getGroup];if {$group ne "NULL"} {set group [$group getName]}
 puts $f [join [list current 5 [$inst getName] [[$inst getMaster] getName] [$inst getLocation] [$inst getOrient] [$inst getPlacementStatus] $group [$b xMin] [$b yMin] [$b xMax] [$b yMax]] "	"]
 foreach term [$inst getITerms] {
  if {[[$term getMTerm] getSigType] ni {POWER GROUND}} {continue}
  set net [$term getNet];if {$net ne "NULL"} {set net [$net getName]}
  puts $f [join [list PG [$inst getName] [[$term getMTerm] getName] $net] "	"]
 }
}
set bounds [list 301.155 1341.775 303.225 1343.845]
foreach inst [$block getInsts] {
 set b [$inst getBBox];lassign $bounds x1 y1 x2 y2
 if {[$b xMin]>$x2*$dbu || [$b xMax]<$x1*$dbu || [$b yMin]>$y2*$dbu || [$b yMax]<$y1*$dbu} {continue}
 set group [$inst getGroup];if {$group ne "NULL"} {set group [$group getName]}
 puts $f [join [list current 6 [$inst getName] [[$inst getMaster] getName] [$inst getLocation] [$inst getOrient] [$inst getPlacementStatus] $group [$b xMin] [$b yMin] [$b xMax] [$b yMax]] "	"]
 foreach term [$inst getITerms] {
  if {[[$term getMTerm] getSigType] ni {POWER GROUND}} {continue}
  set net [$term getNet];if {$net ne "NULL"} {set net [$net getName]}
  puts $f [join [list PG [$inst getName] [[$term getMTerm] getName] $net] "	"]
 }
}
set bounds [list 301.725 1341.775 303.79 1343.845]
foreach inst [$block getInsts] {
 set b [$inst getBBox];lassign $bounds x1 y1 x2 y2
 if {[$b xMin]>$x2*$dbu || [$b xMax]<$x1*$dbu || [$b yMin]>$y2*$dbu || [$b yMax]<$y1*$dbu} {continue}
 set group [$inst getGroup];if {$group ne "NULL"} {set group [$group getName]}
 puts $f [join [list current 7 [$inst getName] [[$inst getMaster] getName] [$inst getLocation] [$inst getOrient] [$inst getPlacementStatus] $group [$b xMin] [$b yMin] [$b xMax] [$b yMax]] "	"]
 foreach term [$inst getITerms] {
  if {[[$term getMTerm] getSigType] ni {POWER GROUND}} {continue}
  set net [$term getNet];if {$net ne "NULL"} {set net [$net getName]}
  puts $f [join [list PG [$inst getName] [[$term getMTerm] getName] $net] "	"]
 }
}
set bounds [list 301.79 1341.775 303.795 1343.845]
foreach inst [$block getInsts] {
 set b [$inst getBBox];lassign $bounds x1 y1 x2 y2
 if {[$b xMin]>$x2*$dbu || [$b xMax]<$x1*$dbu || [$b yMin]>$y2*$dbu || [$b yMax]<$y1*$dbu} {continue}
 set group [$inst getGroup];if {$group ne "NULL"} {set group [$group getName]}
 puts $f [join [list current 8 [$inst getName] [[$inst getMaster] getName] [$inst getLocation] [$inst getOrient] [$inst getPlacementStatus] $group [$b xMin] [$b yMin] [$b xMax] [$b yMax]] "	"]
 foreach term [$inst getITerms] {
  if {[[$term getMTerm] getSigType] ni {POWER GROUND}} {continue}
  set net [$term getNet];if {$net ne "NULL"} {set net [$net getName]}
  puts $f [join [list PG [$inst getName] [[$term getMTerm] getName] $net] "	"]
 }
}
set bounds [list 1592.57 1660.975 1594.64 1663.045]
foreach inst [$block getInsts] {
 set b [$inst getBBox];lassign $bounds x1 y1 x2 y2
 if {[$b xMin]>$x2*$dbu || [$b xMax]<$x1*$dbu || [$b yMin]>$y2*$dbu || [$b yMax]<$y1*$dbu} {continue}
 set group [$inst getGroup];if {$group ne "NULL"} {set group [$group getName]}
 puts $f [join [list current 9 [$inst getName] [[$inst getMaster] getName] [$inst getLocation] [$inst getOrient] [$inst getPlacementStatus] $group [$b xMin] [$b yMin] [$b xMax] [$b yMax]] "	"]
 foreach term [$inst getITerms] {
  if {[[$term getMTerm] getSigType] ni {POWER GROUND}} {continue}
  set net [$term getNet];if {$net ne "NULL"} {set net [$net getName]}
  puts $f [join [list PG [$inst getName] [[$term getMTerm] getName] $net] "	"]
 }
}
set bounds [list 1592.945 1660.975 1595.015 1663.045]
foreach inst [$block getInsts] {
 set b [$inst getBBox];lassign $bounds x1 y1 x2 y2
 if {[$b xMin]>$x2*$dbu || [$b xMax]<$x1*$dbu || [$b yMin]>$y2*$dbu || [$b yMax]<$y1*$dbu} {continue}
 set group [$inst getGroup];if {$group ne "NULL"} {set group [$group getName]}
 puts $f [join [list current 10 [$inst getName] [[$inst getMaster] getName] [$inst getLocation] [$inst getOrient] [$inst getPlacementStatus] $group [$b xMin] [$b yMin] [$b xMax] [$b yMax]] "	"]
 foreach term [$inst getITerms] {
  if {[[$term getMTerm] getSigType] ni {POWER GROUND}} {continue}
  set net [$term getNet];if {$net ne "NULL"} {set net [$net getName]}
  puts $f [join [list PG [$inst getName] [[$term getMTerm] getName] $net] "	"]
 }
}
set bounds [list 1593.325 1660.975 1595.395 1663.045]
foreach inst [$block getInsts] {
 set b [$inst getBBox];lassign $bounds x1 y1 x2 y2
 if {[$b xMin]>$x2*$dbu || [$b xMax]<$x1*$dbu || [$b yMin]>$y2*$dbu || [$b yMax]<$y1*$dbu} {continue}
 set group [$inst getGroup];if {$group ne "NULL"} {set group [$group getName]}
 puts $f [join [list current 11 [$inst getName] [[$inst getMaster] getName] [$inst getLocation] [$inst getOrient] [$inst getPlacementStatus] $group [$b xMin] [$b yMin] [$b xMax] [$b yMax]] "	"]
 foreach term [$inst getITerms] {
  if {[[$term getMTerm] getSigType] ni {POWER GROUND}} {continue}
  set net [$term getNet];if {$net ne "NULL"} {set net [$net getName]}
  puts $f [join [list PG [$inst getName] [[$term getMTerm] getName] $net] "	"]
 }
}
set bounds [list 1593.705 1660.975 1595.775 1663.045]
foreach inst [$block getInsts] {
 set b [$inst getBBox];lassign $bounds x1 y1 x2 y2
 if {[$b xMin]>$x2*$dbu || [$b xMax]<$x1*$dbu || [$b yMin]>$y2*$dbu || [$b yMax]<$y1*$dbu} {continue}
 set group [$inst getGroup];if {$group ne "NULL"} {set group [$group getName]}
 puts $f [join [list current 12 [$inst getName] [[$inst getMaster] getName] [$inst getLocation] [$inst getOrient] [$inst getPlacementStatus] $group [$b xMin] [$b yMin] [$b xMax] [$b yMax]] "	"]
 foreach term [$inst getITerms] {
  if {[[$term getMTerm] getSigType] ni {POWER GROUND}} {continue}
  set net [$term getNet];if {$net ne "NULL"} {set net [$net getName]}
  puts $f [join [list PG [$inst getName] [[$term getMTerm] getName] $net] "	"]
 }
}
set bounds [list 1767.745 207.36 1769.76 209.425]
foreach inst [$block getInsts] {
 set b [$inst getBBox];lassign $bounds x1 y1 x2 y2
 if {[$b xMin]>$x2*$dbu || [$b xMax]<$x1*$dbu || [$b yMin]>$y2*$dbu || [$b yMax]<$y1*$dbu} {continue}
 set group [$inst getGroup];if {$group ne "NULL"} {set group [$group getName]}
 puts $f [join [list current 13 [$inst getName] [[$inst getMaster] getName] [$inst getLocation] [$inst getOrient] [$inst getPlacementStatus] $group [$b xMin] [$b yMin] [$b xMax] [$b yMax]] "	"]
 foreach term [$inst getITerms] {
  if {[[$term getMTerm] getSigType] ni {POWER GROUND}} {continue}
  set net [$term getNet];if {$net ne "NULL"} {set net [$net getName]}
  puts $f [join [list PG [$inst getName] [[$term getMTerm] getName] $net] "	"]
 }
}
set bounds [list 1767.76 207.36 1769.815 209.425]
foreach inst [$block getInsts] {
 set b [$inst getBBox];lassign $bounds x1 y1 x2 y2
 if {[$b xMin]>$x2*$dbu || [$b xMax]<$x1*$dbu || [$b yMin]>$y2*$dbu || [$b yMax]<$y1*$dbu} {continue}
 set group [$inst getGroup];if {$group ne "NULL"} {set group [$group getName]}
 puts $f [join [list current 14 [$inst getName] [[$inst getMaster] getName] [$inst getLocation] [$inst getOrient] [$inst getPlacementStatus] $group [$b xMin] [$b yMin] [$b xMax] [$b yMax]] "	"]
 foreach term [$inst getITerms] {
  if {[[$term getMTerm] getSigType] ni {POWER GROUND}} {continue}
  set net [$term getNet];if {$net ne "NULL"} {set net [$net getName]}
  puts $f [join [list PG [$inst getName] [[$term getMTerm] getName] $net] "	"]
 }
}
set bounds [list 565.045 473.775 567.115 475.845]
foreach inst [$block getInsts] {
 set b [$inst getBBox];lassign $bounds x1 y1 x2 y2
 if {[$b xMin]>$x2*$dbu || [$b xMax]<$x1*$dbu || [$b yMin]>$y2*$dbu || [$b yMax]<$y1*$dbu} {continue}
 set group [$inst getGroup];if {$group ne "NULL"} {set group [$group getName]}
 puts $f [join [list current 15 [$inst getName] [[$inst getMaster] getName] [$inst getLocation] [$inst getOrient] [$inst getPlacementStatus] $group [$b xMin] [$b yMin] [$b xMax] [$b yMax]] "	"]
 foreach term [$inst getITerms] {
  if {[[$term getMTerm] getSigType] ni {POWER GROUND}} {continue}
  set net [$term getNet];if {$net ne "NULL"} {set net [$net getName]}
  puts $f [join [list PG [$inst getName] [[$term getMTerm] getName] $net] "	"]
 }
}
set bounds [list 517.93 680.975 520.0 683.045]
foreach inst [$block getInsts] {
 set b [$inst getBBox];lassign $bounds x1 y1 x2 y2
 if {[$b xMin]>$x2*$dbu || [$b xMax]<$x1*$dbu || [$b yMin]>$y2*$dbu || [$b yMax]<$y1*$dbu} {continue}
 set group [$inst getGroup];if {$group ne "NULL"} {set group [$group getName]}
 puts $f [join [list current 16 [$inst getName] [[$inst getMaster] getName] [$inst getLocation] [$inst getOrient] [$inst getPlacementStatus] $group [$b xMin] [$b yMin] [$b xMax] [$b yMax]] "	"]
 foreach term [$inst getITerms] {
  if {[[$term getMTerm] getSigType] ni {POWER GROUND}} {continue}
  set net [$term getNet];if {$net ne "NULL"} {set net [$net getName]}
  puts $f [join [list PG [$inst getName] [[$term getMTerm] getName] $net] "	"]
 }
}
close $f
