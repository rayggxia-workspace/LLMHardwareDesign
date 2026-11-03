set_thread_count 16
set f [open cells_current.tsv w]
read_db {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-166-r-local-state/attempt628/physical/CLOCK_POST_RESTORE.odb}
set block [ord::get_db_block]
set dbu [$block getDbUnitsPerMicron]
set bounds [list 352.645 1561.575 354.715 1563.645]
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
set bounds [list 352.65 1561.575 354.715 1563.645]
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
set bounds [list 836.005 1068.355 838.075 1070.425]
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
set bounds [list 70.48 237.315 72.55 239.385]
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
set bounds [list 70.855 237.315 72.925 239.385]
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
set bounds [list 71.235 237.315 73.305 239.385]
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
set bounds [list 71.615 237.315 73.685 239.385]
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
set bounds [list 1700.675 1642.355 1702.73 1644.425]
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
set bounds [list 1700.7 1642.355 1702.73 1644.425]
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
set bounds [list 1700.73 1642.355 1702.745 1644.425]
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
set bounds [list 1529.695 1211.575 1531.73 1213.645]
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
set bounds [list 1529.7 1211.575 1531.73 1213.645]
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
set bounds [list 1529.73 1211.575 1531.765 1213.645]
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
set bounds [list 1530.265 1211.575 1532.335 1213.645]
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
set bounds [list 1525.325 477.555 1527.395 479.625]
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
set bounds [list 1525.895 477.555 1527.96 479.625]
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
set bounds [list 1525.96 477.555 1527.965 479.625]
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
set bounds [list 1733.945 71.975 1736.015 74.045]
foreach inst [$block getInsts] {
 set b [$inst getBBox];lassign $bounds x1 y1 x2 y2
 if {[$b xMin]>$x2*$dbu || [$b xMax]<$x1*$dbu || [$b yMin]>$y2*$dbu || [$b yMax]<$y1*$dbu} {continue}
 set group [$inst getGroup];if {$group ne "NULL"} {set group [$group getName]}
 puts $f [join [list current 17 [$inst getName] [[$inst getMaster] getName] [$inst getLocation] [$inst getOrient] [$inst getPlacementStatus] $group [$b xMin] [$b yMin] [$b xMax] [$b yMax]] "	"]
 foreach term [$inst getITerms] {
  if {[[$term getMTerm] getSigType] ni {POWER GROUND}} {continue}
  set net [$term getNet];if {$net ne "NULL"} {set net [$net getName]}
  puts $f [join [list PG [$inst getName] [[$term getMTerm] getName] $net] "	"]
 }
}
set bounds [list 1734.515 71.975 1736.58 74.045]
foreach inst [$block getInsts] {
 set b [$inst getBBox];lassign $bounds x1 y1 x2 y2
 if {[$b xMin]>$x2*$dbu || [$b xMax]<$x1*$dbu || [$b yMin]>$y2*$dbu || [$b yMax]<$y1*$dbu} {continue}
 set group [$inst getGroup];if {$group ne "NULL"} {set group [$group getName]}
 puts $f [join [list current 18 [$inst getName] [[$inst getMaster] getName] [$inst getLocation] [$inst getOrient] [$inst getPlacementStatus] $group [$b xMin] [$b yMin] [$b xMax] [$b yMax]] "	"]
 foreach term [$inst getITerms] {
  if {[[$term getMTerm] getSigType] ni {POWER GROUND}} {continue}
  set net [$term getNet];if {$net ne "NULL"} {set net [$net getName]}
  puts $f [join [list PG [$inst getName] [[$term getMTerm] getName] $net] "	"]
 }
}
set bounds [list 1734.58 71.975 1736.585 74.045]
foreach inst [$block getInsts] {
 set b [$inst getBBox];lassign $bounds x1 y1 x2 y2
 if {[$b xMin]>$x2*$dbu || [$b xMax]<$x1*$dbu || [$b yMin]>$y2*$dbu || [$b yMax]<$y1*$dbu} {continue}
 set group [$inst getGroup];if {$group ne "NULL"} {set group [$group getName]}
 puts $f [join [list current 19 [$inst getName] [[$inst getMaster] getName] [$inst getLocation] [$inst getOrient] [$inst getPlacementStatus] $group [$b xMin] [$b yMin] [$b xMax] [$b yMax]] "	"]
 foreach term [$inst getITerms] {
  if {[[$term getMTerm] getSigType] ni {POWER GROUND}} {continue}
  set net [$term getNet];if {$net ne "NULL"} {set net [$net getName]}
  puts $f [join [list PG [$inst getName] [[$term getMTerm] getName] $net] "	"]
 }
}
set bounds [list 834.295 735.155 836.365 737.225]
foreach inst [$block getInsts] {
 set b [$inst getBBox];lassign $bounds x1 y1 x2 y2
 if {[$b xMin]>$x2*$dbu || [$b xMax]<$x1*$dbu || [$b yMin]>$y2*$dbu || [$b yMax]<$y1*$dbu} {continue}
 set group [$inst getGroup];if {$group ne "NULL"} {set group [$group getName]}
 puts $f [join [list current 20 [$inst getName] [[$inst getMaster] getName] [$inst getLocation] [$inst getOrient] [$inst getPlacementStatus] $group [$b xMin] [$b yMin] [$b xMax] [$b yMax]] "	"]
 foreach term [$inst getITerms] {
  if {[[$term getMTerm] getSigType] ni {POWER GROUND}} {continue}
  set net [$term getNet];if {$net ne "NULL"} {set net [$net getName]}
  puts $f [join [list PG [$inst getName] [[$term getMTerm] getName] $net] "	"]
 }
}
set bounds [list 639.545 569.955 641.58 572.025]
foreach inst [$block getInsts] {
 set b [$inst getBBox];lassign $bounds x1 y1 x2 y2
 if {[$b xMin]>$x2*$dbu || [$b xMax]<$x1*$dbu || [$b yMin]>$y2*$dbu || [$b yMax]<$y1*$dbu} {continue}
 set group [$inst getGroup];if {$group ne "NULL"} {set group [$group getName]}
 puts $f [join [list current 21 [$inst getName] [[$inst getMaster] getName] [$inst getLocation] [$inst getOrient] [$inst getPlacementStatus] $group [$b xMin] [$b yMin] [$b xMax] [$b yMax]] "	"]
 foreach term [$inst getITerms] {
  if {[[$term getMTerm] getSigType] ni {POWER GROUND}} {continue}
  set net [$term getNet];if {$net ne "NULL"} {set net [$net getName]}
  puts $f [join [list PG [$inst getName] [[$term getMTerm] getName] $net] "	"]
 }
}
set bounds [list 639.58 569.955 641.615 572.025]
foreach inst [$block getInsts] {
 set b [$inst getBBox];lassign $bounds x1 y1 x2 y2
 if {[$b xMin]>$x2*$dbu || [$b xMax]<$x1*$dbu || [$b yMin]>$y2*$dbu || [$b yMax]<$y1*$dbu} {continue}
 set group [$inst getGroup];if {$group ne "NULL"} {set group [$group getName]}
 puts $f [join [list current 22 [$inst getName] [[$inst getMaster] getName] [$inst getLocation] [$inst getOrient] [$inst getPlacementStatus] $group [$b xMin] [$b yMin] [$b xMax] [$b yMax]] "	"]
 foreach term [$inst getITerms] {
  if {[[$term getMTerm] getSigType] ni {POWER GROUND}} {continue}
  set net [$term getNet];if {$net ne "NULL"} {set net [$net getName]}
  puts $f [join [list PG [$inst getName] [[$term getMTerm] getName] $net] "	"]
 }
}
set bounds [list 631.375 564.775 633.445 566.845]
foreach inst [$block getInsts] {
 set b [$inst getBBox];lassign $bounds x1 y1 x2 y2
 if {[$b xMin]>$x2*$dbu || [$b xMax]<$x1*$dbu || [$b yMin]>$y2*$dbu || [$b yMax]<$y1*$dbu} {continue}
 set group [$inst getGroup];if {$group ne "NULL"} {set group [$group getName]}
 puts $f [join [list current 23 [$inst getName] [[$inst getMaster] getName] [$inst getLocation] [$inst getOrient] [$inst getPlacementStatus] $group [$b xMin] [$b yMin] [$b xMax] [$b yMax]] "	"]
 foreach term [$inst getITerms] {
  if {[[$term getMTerm] getSigType] ni {POWER GROUND}} {continue}
  set net [$term getNet];if {$net ne "NULL"} {set net [$net getName]}
  puts $f [join [list PG [$inst getName] [[$term getMTerm] getName] $net] "	"]
 }
}
set bounds [list 631.945 564.775 634.0 566.845]
foreach inst [$block getInsts] {
 set b [$inst getBBox];lassign $bounds x1 y1 x2 y2
 if {[$b xMin]>$x2*$dbu || [$b xMax]<$x1*$dbu || [$b yMin]>$y2*$dbu || [$b yMax]<$y1*$dbu} {continue}
 set group [$inst getGroup];if {$group ne "NULL"} {set group [$group getName]}
 puts $f [join [list current 24 [$inst getName] [[$inst getMaster] getName] [$inst getLocation] [$inst getOrient] [$inst getPlacementStatus] $group [$b xMin] [$b yMin] [$b xMax] [$b yMax]] "	"]
 foreach term [$inst getITerms] {
  if {[[$term getMTerm] getSigType] ni {POWER GROUND}} {continue}
  set net [$term getNet];if {$net ne "NULL"} {set net [$net getName]}
  puts $f [join [list PG [$inst getName] [[$term getMTerm] getName] $net] "	"]
 }
}
set bounds [list 632.0 564.775 634.015 566.845]
foreach inst [$block getInsts] {
 set b [$inst getBBox];lassign $bounds x1 y1 x2 y2
 if {[$b xMin]>$x2*$dbu || [$b xMax]<$x1*$dbu || [$b yMin]>$y2*$dbu || [$b yMax]<$y1*$dbu} {continue}
 set group [$inst getGroup];if {$group ne "NULL"} {set group [$group getName]}
 puts $f [join [list current 25 [$inst getName] [[$inst getMaster] getName] [$inst getLocation] [$inst getOrient] [$inst getPlacementStatus] $group [$b xMin] [$b yMin] [$b xMax] [$b yMax]] "	"]
 foreach term [$inst getITerms] {
  if {[[$term getMTerm] getSigType] ni {POWER GROUND}} {continue}
  set net [$term getNet];if {$net ne "NULL"} {set net [$net getName]}
  puts $f [join [list PG [$inst getName] [[$term getMTerm] getName] $net] "	"]
 }
}
set bounds [list 544.91 455.575 546.98 457.645]
foreach inst [$block getInsts] {
 set b [$inst getBBox];lassign $bounds x1 y1 x2 y2
 if {[$b xMin]>$x2*$dbu || [$b xMax]<$x1*$dbu || [$b yMin]>$y2*$dbu || [$b yMax]<$y1*$dbu} {continue}
 set group [$inst getGroup];if {$group ne "NULL"} {set group [$group getName]}
 puts $f [join [list current 26 [$inst getName] [[$inst getMaster] getName] [$inst getLocation] [$inst getOrient] [$inst getPlacementStatus] $group [$b xMin] [$b yMin] [$b xMax] [$b yMax]] "	"]
 foreach term [$inst getITerms] {
  if {[[$term getMTerm] getSigType] ni {POWER GROUND}} {continue}
  set net [$term getNet];if {$net ne "NULL"} {set net [$net getName]}
  puts $f [join [list PG [$inst getName] [[$term getMTerm] getName] $net] "	"]
 }
}
set bounds [list 545.285 455.575 547.305 457.645]
foreach inst [$block getInsts] {
 set b [$inst getBBox];lassign $bounds x1 y1 x2 y2
 if {[$b xMin]>$x2*$dbu || [$b xMax]<$x1*$dbu || [$b yMin]>$y2*$dbu || [$b yMax]<$y1*$dbu} {continue}
 set group [$inst getGroup];if {$group ne "NULL"} {set group [$group getName]}
 puts $f [join [list current 27 [$inst getName] [[$inst getMaster] getName] [$inst getLocation] [$inst getOrient] [$inst getPlacementStatus] $group [$b xMin] [$b yMin] [$b xMax] [$b yMax]] "	"]
 foreach term [$inst getITerms] {
  if {[[$term getMTerm] getSigType] ni {POWER GROUND}} {continue}
  set net [$term getNet];if {$net ne "NULL"} {set net [$net getName]}
  puts $f [join [list PG [$inst getName] [[$term getMTerm] getName] $net] "	"]
 }
}
set bounds [list 545.305 455.575 547.355 457.645]
foreach inst [$block getInsts] {
 set b [$inst getBBox];lassign $bounds x1 y1 x2 y2
 if {[$b xMin]>$x2*$dbu || [$b xMax]<$x1*$dbu || [$b yMin]>$y2*$dbu || [$b yMax]<$y1*$dbu} {continue}
 set group [$inst getGroup];if {$group ne "NULL"} {set group [$group getName]}
 puts $f [join [list current 28 [$inst getName] [[$inst getMaster] getName] [$inst getLocation] [$inst getOrient] [$inst getPlacementStatus] $group [$b xMin] [$b yMin] [$b xMax] [$b yMax]] "	"]
 foreach term [$inst getITerms] {
  if {[[$term getMTerm] getSigType] ni {POWER GROUND}} {continue}
  set net [$term getNet];if {$net ne "NULL"} {set net [$net getName]}
  puts $f [join [list PG [$inst getName] [[$term getMTerm] getName] $net] "	"]
 }
}
set bounds [list 567.71 617.415 569.78 619.485]
foreach inst [$block getInsts] {
 set b [$inst getBBox];lassign $bounds x1 y1 x2 y2
 if {[$b xMin]>$x2*$dbu || [$b xMax]<$x1*$dbu || [$b yMin]>$y2*$dbu || [$b yMax]<$y1*$dbu} {continue}
 set group [$inst getGroup];if {$group ne "NULL"} {set group [$group getName]}
 puts $f [join [list current 29 [$inst getName] [[$inst getMaster] getName] [$inst getLocation] [$inst getOrient] [$inst getPlacementStatus] $group [$b xMin] [$b yMin] [$b xMax] [$b yMax]] "	"]
 foreach term [$inst getITerms] {
  if {[[$term getMTerm] getSigType] ni {POWER GROUND}} {continue}
  set net [$term getNet];if {$net ne "NULL"} {set net [$net getName]}
  puts $f [join [list PG [$inst getName] [[$term getMTerm] getName] $net] "	"]
 }
}
set bounds [list 568.085 617.415 570.155 619.485]
foreach inst [$block getInsts] {
 set b [$inst getBBox];lassign $bounds x1 y1 x2 y2
 if {[$b xMin]>$x2*$dbu || [$b xMax]<$x1*$dbu || [$b yMin]>$y2*$dbu || [$b yMax]<$y1*$dbu} {continue}
 set group [$inst getGroup];if {$group ne "NULL"} {set group [$group getName]}
 puts $f [join [list current 30 [$inst getName] [[$inst getMaster] getName] [$inst getLocation] [$inst getOrient] [$inst getPlacementStatus] $group [$b xMin] [$b yMin] [$b xMax] [$b yMax]] "	"]
 foreach term [$inst getITerms] {
  if {[[$term getMTerm] getSigType] ni {POWER GROUND}} {continue}
  set net [$term getNet];if {$net ne "NULL"} {set net [$net getName]}
  puts $f [join [list PG [$inst getName] [[$term getMTerm] getName] $net] "	"]
 }
}
set bounds [list 568.465 617.415 570.535 619.485]
foreach inst [$block getInsts] {
 set b [$inst getBBox];lassign $bounds x1 y1 x2 y2
 if {[$b xMin]>$x2*$dbu || [$b xMax]<$x1*$dbu || [$b yMin]>$y2*$dbu || [$b yMax]<$y1*$dbu} {continue}
 set group [$inst getGroup];if {$group ne "NULL"} {set group [$group getName]}
 puts $f [join [list current 31 [$inst getName] [[$inst getMaster] getName] [$inst getLocation] [$inst getOrient] [$inst getPlacementStatus] $group [$b xMin] [$b yMin] [$b xMax] [$b yMax]] "	"]
 foreach term [$inst getITerms] {
  if {[[$term getMTerm] getSigType] ni {POWER GROUND}} {continue}
  set net [$term getNet];if {$net ne "NULL"} {set net [$net getName]}
  puts $f [join [list PG [$inst getName] [[$term getMTerm] getName] $net] "	"]
 }
}
set bounds [list 568.845 617.415 570.915 619.485]
foreach inst [$block getInsts] {
 set b [$inst getBBox];lassign $bounds x1 y1 x2 y2
 if {[$b xMin]>$x2*$dbu || [$b xMax]<$x1*$dbu || [$b yMin]>$y2*$dbu || [$b yMax]<$y1*$dbu} {continue}
 set group [$inst getGroup];if {$group ne "NULL"} {set group [$group getName]}
 puts $f [join [list current 32 [$inst getName] [[$inst getMaster] getName] [$inst getLocation] [$inst getOrient] [$inst getPlacementStatus] $group [$b xMin] [$b yMin] [$b xMax] [$b yMax]] "	"]
 foreach term [$inst getITerms] {
  if {[[$term getMTerm] getSigType] ni {POWER GROUND}} {continue}
  set net [$term getNet];if {$net ne "NULL"} {set net [$net getName]}
  puts $f [join [list PG [$inst getName] [[$term getMTerm] getName] $net] "	"]
 }
}
set bounds [list 614.845 1046.375 616.915 1048.445]
foreach inst [$block getInsts] {
 set b [$inst getBBox];lassign $bounds x1 y1 x2 y2
 if {[$b xMin]>$x2*$dbu || [$b xMax]<$x1*$dbu || [$b yMin]>$y2*$dbu || [$b yMax]<$y1*$dbu} {continue}
 set group [$inst getGroup];if {$group ne "NULL"} {set group [$group getName]}
 puts $f [join [list current 33 [$inst getName] [[$inst getMaster] getName] [$inst getLocation] [$inst getOrient] [$inst getPlacementStatus] $group [$b xMin] [$b yMin] [$b xMax] [$b yMax]] "	"]
 foreach term [$inst getITerms] {
  if {[[$term getMTerm] getSigType] ni {POWER GROUND}} {continue}
  set net [$term getNet];if {$net ne "NULL"} {set net [$net getName]}
  puts $f [join [list PG [$inst getName] [[$term getMTerm] getName] $net] "	"]
 }
}
set bounds [list 69.545 1117.355 71.615 1119.425]
foreach inst [$block getInsts] {
 set b [$inst getBBox];lassign $bounds x1 y1 x2 y2
 if {[$b xMin]>$x2*$dbu || [$b xMax]<$x1*$dbu || [$b yMin]>$y2*$dbu || [$b yMax]<$y1*$dbu} {continue}
 set group [$inst getGroup];if {$group ne "NULL"} {set group [$group getName]}
 puts $f [join [list current 34 [$inst getName] [[$inst getMaster] getName] [$inst getLocation] [$inst getOrient] [$inst getPlacementStatus] $group [$b xMin] [$b yMin] [$b xMax] [$b yMax]] "	"]
 foreach term [$inst getITerms] {
  if {[[$term getMTerm] getSigType] ni {POWER GROUND}} {continue}
  set net [$term getNet];if {$net ne "NULL"} {set net [$net getName]}
  puts $f [join [list PG [$inst getName] [[$term getMTerm] getName] $net] "	"]
 }
}
set bounds [list 70.115 1117.355 72.18 1119.425]
foreach inst [$block getInsts] {
 set b [$inst getBBox];lassign $bounds x1 y1 x2 y2
 if {[$b xMin]>$x2*$dbu || [$b xMax]<$x1*$dbu || [$b yMin]>$y2*$dbu || [$b yMax]<$y1*$dbu} {continue}
 set group [$inst getGroup];if {$group ne "NULL"} {set group [$group getName]}
 puts $f [join [list current 35 [$inst getName] [[$inst getMaster] getName] [$inst getLocation] [$inst getOrient] [$inst getPlacementStatus] $group [$b xMin] [$b yMin] [$b xMax] [$b yMax]] "	"]
 foreach term [$inst getITerms] {
  if {[[$term getMTerm] getSigType] ni {POWER GROUND}} {continue}
  set net [$term getNet];if {$net ne "NULL"} {set net [$net getName]}
  puts $f [join [list PG [$inst getName] [[$term getMTerm] getName] $net] "	"]
 }
}
set bounds [list 70.18 1117.355 72.185 1119.425]
foreach inst [$block getInsts] {
 set b [$inst getBBox];lassign $bounds x1 y1 x2 y2
 if {[$b xMin]>$x2*$dbu || [$b xMax]<$x1*$dbu || [$b yMin]>$y2*$dbu || [$b yMax]<$y1*$dbu} {continue}
 set group [$inst getGroup];if {$group ne "NULL"} {set group [$group getName]}
 puts $f [join [list current 36 [$inst getName] [[$inst getMaster] getName] [$inst getLocation] [$inst getOrient] [$inst getPlacementStatus] $group [$b xMin] [$b yMin] [$b xMax] [$b yMax]] "	"]
 foreach term [$inst getITerms] {
  if {[[$term getMTerm] getSigType] ni {POWER GROUND}} {continue}
  set net [$term getNet];if {$net ne "NULL"} {set net [$net getName]}
  puts $f [join [list PG [$inst getName] [[$term getMTerm] getName] $net] "	"]
 }
}
set bounds [list 536.36 1332.955 538.43 1335.025]
foreach inst [$block getInsts] {
 set b [$inst getBBox];lassign $bounds x1 y1 x2 y2
 if {[$b xMin]>$x2*$dbu || [$b xMax]<$x1*$dbu || [$b yMin]>$y2*$dbu || [$b yMax]<$y1*$dbu} {continue}
 set group [$inst getGroup];if {$group ne "NULL"} {set group [$group getName]}
 puts $f [join [list current 37 [$inst getName] [[$inst getMaster] getName] [$inst getLocation] [$inst getOrient] [$inst getPlacementStatus] $group [$b xMin] [$b yMin] [$b xMax] [$b yMax]] "	"]
 foreach term [$inst getITerms] {
  if {[[$term getMTerm] getSigType] ni {POWER GROUND}} {continue}
  set net [$term getNet];if {$net ne "NULL"} {set net [$net getName]}
  puts $f [join [list PG [$inst getName] [[$term getMTerm] getName] $net] "	"]
 }
}
set bounds [list 536.735 1332.955 538.805 1335.025]
foreach inst [$block getInsts] {
 set b [$inst getBBox];lassign $bounds x1 y1 x2 y2
 if {[$b xMin]>$x2*$dbu || [$b xMax]<$x1*$dbu || [$b yMin]>$y2*$dbu || [$b yMax]<$y1*$dbu} {continue}
 set group [$inst getGroup];if {$group ne "NULL"} {set group [$group getName]}
 puts $f [join [list current 38 [$inst getName] [[$inst getMaster] getName] [$inst getLocation] [$inst getOrient] [$inst getPlacementStatus] $group [$b xMin] [$b yMin] [$b xMax] [$b yMax]] "	"]
 foreach term [$inst getITerms] {
  if {[[$term getMTerm] getSigType] ni {POWER GROUND}} {continue}
  set net [$term getNet];if {$net ne "NULL"} {set net [$net getName]}
  puts $f [join [list PG [$inst getName] [[$term getMTerm] getName] $net] "	"]
 }
}
set bounds [list 537.115 1332.955 539.185 1335.025]
foreach inst [$block getInsts] {
 set b [$inst getBBox];lassign $bounds x1 y1 x2 y2
 if {[$b xMin]>$x2*$dbu || [$b xMax]<$x1*$dbu || [$b yMin]>$y2*$dbu || [$b yMax]<$y1*$dbu} {continue}
 set group [$inst getGroup];if {$group ne "NULL"} {set group [$group getName]}
 puts $f [join [list current 39 [$inst getName] [[$inst getMaster] getName] [$inst getLocation] [$inst getOrient] [$inst getPlacementStatus] $group [$b xMin] [$b yMin] [$b xMax] [$b yMax]] "	"]
 foreach term [$inst getITerms] {
  if {[[$term getMTerm] getSigType] ni {POWER GROUND}} {continue}
  set net [$term getNet];if {$net ne "NULL"} {set net [$net getName]}
  puts $f [join [list PG [$inst getName] [[$term getMTerm] getName] $net] "	"]
 }
}
set bounds [list 537.495 1332.955 539.565 1335.025]
foreach inst [$block getInsts] {
 set b [$inst getBBox];lassign $bounds x1 y1 x2 y2
 if {[$b xMin]>$x2*$dbu || [$b xMax]<$x1*$dbu || [$b yMin]>$y2*$dbu || [$b yMax]<$y1*$dbu} {continue}
 set group [$inst getGroup];if {$group ne "NULL"} {set group [$group getName]}
 puts $f [join [list current 40 [$inst getName] [[$inst getMaster] getName] [$inst getLocation] [$inst getOrient] [$inst getPlacementStatus] $group [$b xMin] [$b yMin] [$b xMax] [$b yMax]] "	"]
 foreach term [$inst getITerms] {
  if {[[$term getMTerm] getSigType] ni {POWER GROUND}} {continue}
  set net [$term getNet];if {$net ne "NULL"} {set net [$net getName]}
  puts $f [join [list PG [$inst getName] [[$term getMTerm] getName] $net] "	"]
 }
}
set bounds [list 533.51 1313.775 535.535 1315.845]
foreach inst [$block getInsts] {
 set b [$inst getBBox];lassign $bounds x1 y1 x2 y2
 if {[$b xMin]>$x2*$dbu || [$b xMax]<$x1*$dbu || [$b yMin]>$y2*$dbu || [$b yMax]<$y1*$dbu} {continue}
 set group [$inst getGroup];if {$group ne "NULL"} {set group [$group getName]}
 puts $f [join [list current 41 [$inst getName] [[$inst getMaster] getName] [$inst getLocation] [$inst getOrient] [$inst getPlacementStatus] $group [$b xMin] [$b yMin] [$b xMax] [$b yMax]] "	"]
 foreach term [$inst getITerms] {
  if {[[$term getMTerm] getSigType] ni {POWER GROUND}} {continue}
  set net [$term getNet];if {$net ne "NULL"} {set net [$net getName]}
  puts $f [join [list PG [$inst getName] [[$term getMTerm] getName] $net] "	"]
 }
}
set bounds [list 533.535 1313.775 535.58 1315.845]
foreach inst [$block getInsts] {
 set b [$inst getBBox];lassign $bounds x1 y1 x2 y2
 if {[$b xMin]>$x2*$dbu || [$b xMax]<$x1*$dbu || [$b yMin]>$y2*$dbu || [$b yMax]<$y1*$dbu} {continue}
 set group [$inst getGroup];if {$group ne "NULL"} {set group [$group getName]}
 puts $f [join [list current 42 [$inst getName] [[$inst getMaster] getName] [$inst getLocation] [$inst getOrient] [$inst getPlacementStatus] $group [$b xMin] [$b yMin] [$b xMax] [$b yMax]] "	"]
 foreach term [$inst getITerms] {
  if {[[$term getMTerm] getSigType] ni {POWER GROUND}} {continue}
  set net [$term getNet];if {$net ne "NULL"} {set net [$net getName]}
  puts $f [join [list PG [$inst getName] [[$term getMTerm] getName] $net] "	"]
 }
}
set bounds [list 533.885 1313.775 535.955 1315.845]
foreach inst [$block getInsts] {
 set b [$inst getBBox];lassign $bounds x1 y1 x2 y2
 if {[$b xMin]>$x2*$dbu || [$b xMax]<$x1*$dbu || [$b yMin]>$y2*$dbu || [$b yMax]<$y1*$dbu} {continue}
 set group [$inst getGroup];if {$group ne "NULL"} {set group [$group getName]}
 puts $f [join [list current 43 [$inst getName] [[$inst getMaster] getName] [$inst getLocation] [$inst getOrient] [$inst getPlacementStatus] $group [$b xMin] [$b yMin] [$b xMax] [$b yMax]] "	"]
 foreach term [$inst getITerms] {
  if {[[$term getMTerm] getSigType] ni {POWER GROUND}} {continue}
  set net [$term getNet];if {$net ne "NULL"} {set net [$net getName]}
  puts $f [join [list PG [$inst getName] [[$term getMTerm] getName] $net] "	"]
 }
}
set bounds [list 534.265 1313.775 536.335 1315.845]
foreach inst [$block getInsts] {
 set b [$inst getBBox];lassign $bounds x1 y1 x2 y2
 if {[$b xMin]>$x2*$dbu || [$b xMax]<$x1*$dbu || [$b yMin]>$y2*$dbu || [$b yMax]<$y1*$dbu} {continue}
 set group [$inst getGroup];if {$group ne "NULL"} {set group [$group getName]}
 puts $f [join [list current 44 [$inst getName] [[$inst getMaster] getName] [$inst getLocation] [$inst getOrient] [$inst getPlacementStatus] $group [$b xMin] [$b yMin] [$b xMax] [$b yMax]] "	"]
 foreach term [$inst getITerms] {
  if {[[$term getMTerm] getSigType] ni {POWER GROUND}} {continue}
  set net [$term getNet];if {$net ne "NULL"} {set net [$net getName]}
  puts $f [join [list PG [$inst getName] [[$term getMTerm] getName] $net] "	"]
 }
}
set bounds [list 534.645 1313.775 536.715 1315.845]
foreach inst [$block getInsts] {
 set b [$inst getBBox];lassign $bounds x1 y1 x2 y2
 if {[$b xMin]>$x2*$dbu || [$b xMax]<$x1*$dbu || [$b yMin]>$y2*$dbu || [$b yMax]<$y1*$dbu} {continue}
 set group [$inst getGroup];if {$group ne "NULL"} {set group [$group getName]}
 puts $f [join [list current 45 [$inst getName] [[$inst getMaster] getName] [$inst getLocation] [$inst getOrient] [$inst getPlacementStatus] $group [$b xMin] [$b yMin] [$b xMax] [$b yMax]] "	"]
 foreach term [$inst getITerms] {
  if {[[$term getMTerm] getSigType] ni {POWER GROUND}} {continue}
  set net [$term getNet];if {$net ne "NULL"} {set net [$net getName]}
  puts $f [join [list PG [$inst getName] [[$term getMTerm] getName] $net] "	"]
 }
}
set bounds [list 877.995 1078.155 880.065 1080.225]
foreach inst [$block getInsts] {
 set b [$inst getBBox];lassign $bounds x1 y1 x2 y2
 if {[$b xMin]>$x2*$dbu || [$b xMax]<$x1*$dbu || [$b yMin]>$y2*$dbu || [$b yMax]<$y1*$dbu} {continue}
 set group [$inst getGroup];if {$group ne "NULL"} {set group [$group getName]}
 puts $f [join [list current 46 [$inst getName] [[$inst getMaster] getName] [$inst getLocation] [$inst getOrient] [$inst getPlacementStatus] $group [$b xMin] [$b yMin] [$b xMax] [$b yMax]] "	"]
 foreach term [$inst getITerms] {
  if {[[$term getMTerm] getSigType] ni {POWER GROUND}} {continue}
  set net [$term getNet];if {$net ne "NULL"} {set net [$net getName]}
  puts $f [join [list PG [$inst getName] [[$term getMTerm] getName] $net] "	"]
 }
}
set bounds [list 401.08 456.555 403.15 458.625]
foreach inst [$block getInsts] {
 set b [$inst getBBox];lassign $bounds x1 y1 x2 y2
 if {[$b xMin]>$x2*$dbu || [$b xMax]<$x1*$dbu || [$b yMin]>$y2*$dbu || [$b yMax]<$y1*$dbu} {continue}
 set group [$inst getGroup];if {$group ne "NULL"} {set group [$group getName]}
 puts $f [join [list current 47 [$inst getName] [[$inst getMaster] getName] [$inst getLocation] [$inst getOrient] [$inst getPlacementStatus] $group [$b xMin] [$b yMin] [$b xMax] [$b yMax]] "	"]
 foreach term [$inst getITerms] {
  if {[[$term getMTerm] getSigType] ni {POWER GROUND}} {continue}
  set net [$term getNet];if {$net ne "NULL"} {set net [$net getName]}
  puts $f [join [list PG [$inst getName] [[$term getMTerm] getName] $net] "	"]
 }
}
set bounds [list 401.455 456.555 403.525 458.625]
foreach inst [$block getInsts] {
 set b [$inst getBBox];lassign $bounds x1 y1 x2 y2
 if {[$b xMin]>$x2*$dbu || [$b xMax]<$x1*$dbu || [$b yMin]>$y2*$dbu || [$b yMax]<$y1*$dbu} {continue}
 set group [$inst getGroup];if {$group ne "NULL"} {set group [$group getName]}
 puts $f [join [list current 48 [$inst getName] [[$inst getMaster] getName] [$inst getLocation] [$inst getOrient] [$inst getPlacementStatus] $group [$b xMin] [$b yMin] [$b xMax] [$b yMax]] "	"]
 foreach term [$inst getITerms] {
  if {[[$term getMTerm] getSigType] ni {POWER GROUND}} {continue}
  set net [$term getNet];if {$net ne "NULL"} {set net [$net getName]}
  puts $f [join [list PG [$inst getName] [[$term getMTerm] getName] $net] "	"]
 }
}
set bounds [list 401.835 456.555 403.905 458.625]
foreach inst [$block getInsts] {
 set b [$inst getBBox];lassign $bounds x1 y1 x2 y2
 if {[$b xMin]>$x2*$dbu || [$b xMax]<$x1*$dbu || [$b yMin]>$y2*$dbu || [$b yMax]<$y1*$dbu} {continue}
 set group [$inst getGroup];if {$group ne "NULL"} {set group [$group getName]}
 puts $f [join [list current 49 [$inst getName] [[$inst getMaster] getName] [$inst getLocation] [$inst getOrient] [$inst getPlacementStatus] $group [$b xMin] [$b yMin] [$b xMax] [$b yMax]] "	"]
 foreach term [$inst getITerms] {
  if {[[$term getMTerm] getSigType] ni {POWER GROUND}} {continue}
  set net [$term getNet];if {$net ne "NULL"} {set net [$net getName]}
  puts $f [join [list PG [$inst getName] [[$term getMTerm] getName] $net] "	"]
 }
}
set bounds [list 402.215 456.555 404.285 458.625]
foreach inst [$block getInsts] {
 set b [$inst getBBox];lassign $bounds x1 y1 x2 y2
 if {[$b xMin]>$x2*$dbu || [$b xMax]<$x1*$dbu || [$b yMin]>$y2*$dbu || [$b yMax]<$y1*$dbu} {continue}
 set group [$inst getGroup];if {$group ne "NULL"} {set group [$group getName]}
 puts $f [join [list current 50 [$inst getName] [[$inst getMaster] getName] [$inst getLocation] [$inst getOrient] [$inst getPlacementStatus] $group [$b xMin] [$b yMin] [$b xMax] [$b yMax]] "	"]
 foreach term [$inst getITerms] {
  if {[[$term getMTerm] getSigType] ni {POWER GROUND}} {continue}
  set net [$term getNet];if {$net ne "NULL"} {set net [$net getName]}
  puts $f [join [list PG [$inst getName] [[$term getMTerm] getName] $net] "	"]
 }
}
set bounds [list 1648.825 1117.355 1650.895 1119.425]
foreach inst [$block getInsts] {
 set b [$inst getBBox];lassign $bounds x1 y1 x2 y2
 if {[$b xMin]>$x2*$dbu || [$b xMax]<$x1*$dbu || [$b yMin]>$y2*$dbu || [$b yMax]<$y1*$dbu} {continue}
 set group [$inst getGroup];if {$group ne "NULL"} {set group [$group getName]}
 puts $f [join [list current 51 [$inst getName] [[$inst getMaster] getName] [$inst getLocation] [$inst getOrient] [$inst getPlacementStatus] $group [$b xMin] [$b yMin] [$b xMax] [$b yMax]] "	"]
 foreach term [$inst getITerms] {
  if {[[$term getMTerm] getSigType] ni {POWER GROUND}} {continue}
  set net [$term getNet];if {$net ne "NULL"} {set net [$net getName]}
  puts $f [join [list PG [$inst getName] [[$term getMTerm] getName] $net] "	"]
 }
}
set bounds [list 1649.395 1117.355 1651.46 1119.425]
foreach inst [$block getInsts] {
 set b [$inst getBBox];lassign $bounds x1 y1 x2 y2
 if {[$b xMin]>$x2*$dbu || [$b xMax]<$x1*$dbu || [$b yMin]>$y2*$dbu || [$b yMax]<$y1*$dbu} {continue}
 set group [$inst getGroup];if {$group ne "NULL"} {set group [$group getName]}
 puts $f [join [list current 52 [$inst getName] [[$inst getMaster] getName] [$inst getLocation] [$inst getOrient] [$inst getPlacementStatus] $group [$b xMin] [$b yMin] [$b xMax] [$b yMax]] "	"]
 foreach term [$inst getITerms] {
  if {[[$term getMTerm] getSigType] ni {POWER GROUND}} {continue}
  set net [$term getNet];if {$net ne "NULL"} {set net [$net getName]}
  puts $f [join [list PG [$inst getName] [[$term getMTerm] getName] $net] "	"]
 }
}
set bounds [list 1649.46 1117.355 1651.465 1119.425]
foreach inst [$block getInsts] {
 set b [$inst getBBox];lassign $bounds x1 y1 x2 y2
 if {[$b xMin]>$x2*$dbu || [$b xMax]<$x1*$dbu || [$b yMin]>$y2*$dbu || [$b yMax]<$y1*$dbu} {continue}
 set group [$inst getGroup];if {$group ne "NULL"} {set group [$group getName]}
 puts $f [join [list current 53 [$inst getName] [[$inst getMaster] getName] [$inst getLocation] [$inst getOrient] [$inst getPlacementStatus] $group [$b xMin] [$b yMin] [$b xMax] [$b yMax]] "	"]
 foreach term [$inst getITerms] {
  if {[[$term getMTerm] getSigType] ni {POWER GROUND}} {continue}
  set net [$term getNet];if {$net ne "NULL"} {set net [$net getName]}
  puts $f [join [list PG [$inst getName] [[$term getMTerm] getName] $net] "	"]
 }
}
set bounds [list 83.605 193.355 85.675 195.425]
foreach inst [$block getInsts] {
 set b [$inst getBBox];lassign $bounds x1 y1 x2 y2
 if {[$b xMin]>$x2*$dbu || [$b xMax]<$x1*$dbu || [$b yMin]>$y2*$dbu || [$b yMax]<$y1*$dbu} {continue}
 set group [$inst getGroup];if {$group ne "NULL"} {set group [$group getName]}
 puts $f [join [list current 54 [$inst getName] [[$inst getMaster] getName] [$inst getLocation] [$inst getOrient] [$inst getPlacementStatus] $group [$b xMin] [$b yMin] [$b xMax] [$b yMax]] "	"]
 foreach term [$inst getITerms] {
  if {[[$term getMTerm] getSigType] ni {POWER GROUND}} {continue}
  set net [$term getNet];if {$net ne "NULL"} {set net [$net getName]}
  puts $f [join [list PG [$inst getName] [[$term getMTerm] getName] $net] "	"]
 }
}
set bounds [list 84.175 193.355 86.24 195.425]
foreach inst [$block getInsts] {
 set b [$inst getBBox];lassign $bounds x1 y1 x2 y2
 if {[$b xMin]>$x2*$dbu || [$b xMax]<$x1*$dbu || [$b yMin]>$y2*$dbu || [$b yMax]<$y1*$dbu} {continue}
 set group [$inst getGroup];if {$group ne "NULL"} {set group [$group getName]}
 puts $f [join [list current 55 [$inst getName] [[$inst getMaster] getName] [$inst getLocation] [$inst getOrient] [$inst getPlacementStatus] $group [$b xMin] [$b yMin] [$b xMax] [$b yMax]] "	"]
 foreach term [$inst getITerms] {
  if {[[$term getMTerm] getSigType] ni {POWER GROUND}} {continue}
  set net [$term getNet];if {$net ne "NULL"} {set net [$net getName]}
  puts $f [join [list PG [$inst getName] [[$term getMTerm] getName] $net] "	"]
 }
}
set bounds [list 84.24 193.355 86.245 195.425]
foreach inst [$block getInsts] {
 set b [$inst getBBox];lassign $bounds x1 y1 x2 y2
 if {[$b xMin]>$x2*$dbu || [$b xMax]<$x1*$dbu || [$b yMin]>$y2*$dbu || [$b yMax]<$y1*$dbu} {continue}
 set group [$inst getGroup];if {$group ne "NULL"} {set group [$group getName]}
 puts $f [join [list current 56 [$inst getName] [[$inst getMaster] getName] [$inst getLocation] [$inst getOrient] [$inst getPlacementStatus] $group [$b xMin] [$b yMin] [$b xMax] [$b yMax]] "	"]
 foreach term [$inst getITerms] {
  if {[[$term getMTerm] getSigType] ni {POWER GROUND}} {continue}
  set net [$term getNet];if {$net ne "NULL"} {set net [$net getName]}
  puts $f [join [list PG [$inst getName] [[$term getMTerm] getName] $net] "	"]
 }
}
set bounds [list 92.535 190.555 94.605 192.625]
foreach inst [$block getInsts] {
 set b [$inst getBBox];lassign $bounds x1 y1 x2 y2
 if {[$b xMin]>$x2*$dbu || [$b xMax]<$x1*$dbu || [$b yMin]>$y2*$dbu || [$b yMax]<$y1*$dbu} {continue}
 set group [$inst getGroup];if {$group ne "NULL"} {set group [$group getName]}
 puts $f [join [list current 57 [$inst getName] [[$inst getMaster] getName] [$inst getLocation] [$inst getOrient] [$inst getPlacementStatus] $group [$b xMin] [$b yMin] [$b xMax] [$b yMax]] "	"]
 foreach term [$inst getITerms] {
  if {[[$term getMTerm] getSigType] ni {POWER GROUND}} {continue}
  set net [$term getNet];if {$net ne "NULL"} {set net [$net getName]}
  puts $f [join [list PG [$inst getName] [[$term getMTerm] getName] $net] "	"]
 }
}
set bounds [list 93.105 190.555 95.17 192.625]
foreach inst [$block getInsts] {
 set b [$inst getBBox];lassign $bounds x1 y1 x2 y2
 if {[$b xMin]>$x2*$dbu || [$b xMax]<$x1*$dbu || [$b yMin]>$y2*$dbu || [$b yMax]<$y1*$dbu} {continue}
 set group [$inst getGroup];if {$group ne "NULL"} {set group [$group getName]}
 puts $f [join [list current 58 [$inst getName] [[$inst getMaster] getName] [$inst getLocation] [$inst getOrient] [$inst getPlacementStatus] $group [$b xMin] [$b yMin] [$b xMax] [$b yMax]] "	"]
 foreach term [$inst getITerms] {
  if {[[$term getMTerm] getSigType] ni {POWER GROUND}} {continue}
  set net [$term getNet];if {$net ne "NULL"} {set net [$net getName]}
  puts $f [join [list PG [$inst getName] [[$term getMTerm] getName] $net] "	"]
 }
}
set bounds [list 93.17 190.555 95.175 192.625]
foreach inst [$block getInsts] {
 set b [$inst getBBox];lassign $bounds x1 y1 x2 y2
 if {[$b xMin]>$x2*$dbu || [$b xMax]<$x1*$dbu || [$b yMin]>$y2*$dbu || [$b yMax]<$y1*$dbu} {continue}
 set group [$inst getGroup];if {$group ne "NULL"} {set group [$group getName]}
 puts $f [join [list current 59 [$inst getName] [[$inst getMaster] getName] [$inst getLocation] [$inst getOrient] [$inst getPlacementStatus] $group [$b xMin] [$b yMin] [$b xMax] [$b yMax]] "	"]
 foreach term [$inst getITerms] {
  if {[[$term getMTerm] getSigType] ni {POWER GROUND}} {continue}
  set net [$term getNet];if {$net ne "NULL"} {set net [$net getName]}
  puts $f [join [list PG [$inst getName] [[$term getMTerm] getName] $net] "	"]
 }
}
set bounds [list 1561.805 456.555 1563.87 458.625]
foreach inst [$block getInsts] {
 set b [$inst getBBox];lassign $bounds x1 y1 x2 y2
 if {[$b xMin]>$x2*$dbu || [$b xMax]<$x1*$dbu || [$b yMin]>$y2*$dbu || [$b yMax]<$y1*$dbu} {continue}
 set group [$inst getGroup];if {$group ne "NULL"} {set group [$group getName]}
 puts $f [join [list current 60 [$inst getName] [[$inst getMaster] getName] [$inst getLocation] [$inst getOrient] [$inst getPlacementStatus] $group [$b xMin] [$b yMin] [$b xMax] [$b yMax]] "	"]
 foreach term [$inst getITerms] {
  if {[[$term getMTerm] getSigType] ni {POWER GROUND}} {continue}
  set net [$term getNet];if {$net ne "NULL"} {set net [$net getName]}
  puts $f [join [list PG [$inst getName] [[$term getMTerm] getName] $net] "	"]
 }
}
set bounds [list 1561.87 456.555 1563.875 458.625]
foreach inst [$block getInsts] {
 set b [$inst getBBox];lassign $bounds x1 y1 x2 y2
 if {[$b xMin]>$x2*$dbu || [$b xMax]<$x1*$dbu || [$b yMin]>$y2*$dbu || [$b yMax]<$y1*$dbu} {continue}
 set group [$inst getGroup];if {$group ne "NULL"} {set group [$group getName]}
 puts $f [join [list current 61 [$inst getName] [[$inst getMaster] getName] [$inst getLocation] [$inst getOrient] [$inst getPlacementStatus] $group [$b xMin] [$b yMin] [$b xMax] [$b yMax]] "	"]
 foreach term [$inst getITerms] {
  if {[[$term getMTerm] getSigType] ni {POWER GROUND}} {continue}
  set net [$term getNet];if {$net ne "NULL"} {set net [$net getName]}
  puts $f [join [list PG [$inst getName] [[$term getMTerm] getName] $net] "	"]
 }
}
set bounds [list 1562.375 456.555 1564.445 458.625]
foreach inst [$block getInsts] {
 set b [$inst getBBox];lassign $bounds x1 y1 x2 y2
 if {[$b xMin]>$x2*$dbu || [$b xMax]<$x1*$dbu || [$b yMin]>$y2*$dbu || [$b yMax]<$y1*$dbu} {continue}
 set group [$inst getGroup];if {$group ne "NULL"} {set group [$group getName]}
 puts $f [join [list current 62 [$inst getName] [[$inst getMaster] getName] [$inst getLocation] [$inst getOrient] [$inst getPlacementStatus] $group [$b xMin] [$b yMin] [$b xMax] [$b yMax]] "	"]
 foreach term [$inst getITerms] {
  if {[[$term getMTerm] getSigType] ni {POWER GROUND}} {continue}
  set net [$term getNet];if {$net ne "NULL"} {set net [$net getName]}
  puts $f [join [list PG [$inst getName] [[$term getMTerm] getName] $net] "	"]
 }
}
set bounds [list 1767.56 207.355 1769.63 209.425]
foreach inst [$block getInsts] {
 set b [$inst getBBox];lassign $bounds x1 y1 x2 y2
 if {[$b xMin]>$x2*$dbu || [$b xMax]<$x1*$dbu || [$b yMin]>$y2*$dbu || [$b yMax]<$y1*$dbu} {continue}
 set group [$inst getGroup];if {$group ne "NULL"} {set group [$group getName]}
 puts $f [join [list current 63 [$inst getName] [[$inst getMaster] getName] [$inst getLocation] [$inst getOrient] [$inst getPlacementStatus] $group [$b xMin] [$b yMin] [$b xMax] [$b yMax]] "	"]
 foreach term [$inst getITerms] {
  if {[[$term getMTerm] getSigType] ni {POWER GROUND}} {continue}
  set net [$term getNet];if {$net ne "NULL"} {set net [$net getName]}
  puts $f [join [list PG [$inst getName] [[$term getMTerm] getName] $net] "	"]
 }
}
set bounds [list 1615.75 128.955 1617.82 131.025]
foreach inst [$block getInsts] {
 set b [$inst getBBox];lassign $bounds x1 y1 x2 y2
 if {[$b xMin]>$x2*$dbu || [$b xMax]<$x1*$dbu || [$b yMin]>$y2*$dbu || [$b yMax]<$y1*$dbu} {continue}
 set group [$inst getGroup];if {$group ne "NULL"} {set group [$group getName]}
 puts $f [join [list current 64 [$inst getName] [[$inst getMaster] getName] [$inst getLocation] [$inst getOrient] [$inst getPlacementStatus] $group [$b xMin] [$b yMin] [$b xMax] [$b yMax]] "	"]
 foreach term [$inst getITerms] {
  if {[[$term getMTerm] getSigType] ni {POWER GROUND}} {continue}
  set net [$term getNet];if {$net ne "NULL"} {set net [$net getName]}
  puts $f [join [list PG [$inst getName] [[$term getMTerm] getName] $net] "	"]
 }
}
set bounds [list 1616.125 128.955 1618.195 131.025]
foreach inst [$block getInsts] {
 set b [$inst getBBox];lassign $bounds x1 y1 x2 y2
 if {[$b xMin]>$x2*$dbu || [$b xMax]<$x1*$dbu || [$b yMin]>$y2*$dbu || [$b yMax]<$y1*$dbu} {continue}
 set group [$inst getGroup];if {$group ne "NULL"} {set group [$group getName]}
 puts $f [join [list current 65 [$inst getName] [[$inst getMaster] getName] [$inst getLocation] [$inst getOrient] [$inst getPlacementStatus] $group [$b xMin] [$b yMin] [$b xMax] [$b yMax]] "	"]
 foreach term [$inst getITerms] {
  if {[[$term getMTerm] getSigType] ni {POWER GROUND}} {continue}
  set net [$term getNet];if {$net ne "NULL"} {set net [$net getName]}
  puts $f [join [list PG [$inst getName] [[$term getMTerm] getName] $net] "	"]
 }
}
set bounds [list 1616.505 128.955 1618.575 131.025]
foreach inst [$block getInsts] {
 set b [$inst getBBox];lassign $bounds x1 y1 x2 y2
 if {[$b xMin]>$x2*$dbu || [$b xMax]<$x1*$dbu || [$b yMin]>$y2*$dbu || [$b yMax]<$y1*$dbu} {continue}
 set group [$inst getGroup];if {$group ne "NULL"} {set group [$group getName]}
 puts $f [join [list current 66 [$inst getName] [[$inst getMaster] getName] [$inst getLocation] [$inst getOrient] [$inst getPlacementStatus] $group [$b xMin] [$b yMin] [$b xMax] [$b yMax]] "	"]
 foreach term [$inst getITerms] {
  if {[[$term getMTerm] getSigType] ni {POWER GROUND}} {continue}
  set net [$term getNet];if {$net ne "NULL"} {set net [$net getName]}
  puts $f [join [list PG [$inst getName] [[$term getMTerm] getName] $net] "	"]
 }
}
set bounds [list 1616.885 128.955 1618.955 131.025]
foreach inst [$block getInsts] {
 set b [$inst getBBox];lassign $bounds x1 y1 x2 y2
 if {[$b xMin]>$x2*$dbu || [$b xMax]<$x1*$dbu || [$b yMin]>$y2*$dbu || [$b yMax]<$y1*$dbu} {continue}
 set group [$inst getGroup];if {$group ne "NULL"} {set group [$group getName]}
 puts $f [join [list current 67 [$inst getName] [[$inst getMaster] getName] [$inst getLocation] [$inst getOrient] [$inst getPlacementStatus] $group [$b xMin] [$b yMin] [$b xMax] [$b yMax]] "	"]
 foreach term [$inst getITerms] {
  if {[[$term getMTerm] getSigType] ni {POWER GROUND}} {continue}
  set net [$term getNet];if {$net ne "NULL"} {set net [$net getName]}
  puts $f [join [list PG [$inst getName] [[$term getMTerm] getName] $net] "	"]
 }
}
set bounds [list 1414.175 145.755 1416.245 147.825]
foreach inst [$block getInsts] {
 set b [$inst getBBox];lassign $bounds x1 y1 x2 y2
 if {[$b xMin]>$x2*$dbu || [$b xMax]<$x1*$dbu || [$b yMin]>$y2*$dbu || [$b yMax]<$y1*$dbu} {continue}
 set group [$inst getGroup];if {$group ne "NULL"} {set group [$group getName]}
 puts $f [join [list current 68 [$inst getName] [[$inst getMaster] getName] [$inst getLocation] [$inst getOrient] [$inst getPlacementStatus] $group [$b xMin] [$b yMin] [$b xMax] [$b yMax]] "	"]
 foreach term [$inst getITerms] {
  if {[[$term getMTerm] getSigType] ni {POWER GROUND}} {continue}
  set net [$term getNet];if {$net ne "NULL"} {set net [$net getName]}
  puts $f [join [list PG [$inst getName] [[$term getMTerm] getName] $net] "	"]
 }
}
set bounds [list 1414.745 145.755 1416.81 147.825]
foreach inst [$block getInsts] {
 set b [$inst getBBox];lassign $bounds x1 y1 x2 y2
 if {[$b xMin]>$x2*$dbu || [$b xMax]<$x1*$dbu || [$b yMin]>$y2*$dbu || [$b yMax]<$y1*$dbu} {continue}
 set group [$inst getGroup];if {$group ne "NULL"} {set group [$group getName]}
 puts $f [join [list current 69 [$inst getName] [[$inst getMaster] getName] [$inst getLocation] [$inst getOrient] [$inst getPlacementStatus] $group [$b xMin] [$b yMin] [$b xMax] [$b yMax]] "	"]
 foreach term [$inst getITerms] {
  if {[[$term getMTerm] getSigType] ni {POWER GROUND}} {continue}
  set net [$term getNet];if {$net ne "NULL"} {set net [$net getName]}
  puts $f [join [list PG [$inst getName] [[$term getMTerm] getName] $net] "	"]
 }
}
set bounds [list 1414.81 145.755 1416.815 147.825]
foreach inst [$block getInsts] {
 set b [$inst getBBox];lassign $bounds x1 y1 x2 y2
 if {[$b xMin]>$x2*$dbu || [$b xMax]<$x1*$dbu || [$b yMin]>$y2*$dbu || [$b yMax]<$y1*$dbu} {continue}
 set group [$inst getGroup];if {$group ne "NULL"} {set group [$group getName]}
 puts $f [join [list current 70 [$inst getName] [[$inst getMaster] getName] [$inst getLocation] [$inst getOrient] [$inst getPlacementStatus] $group [$b xMin] [$b yMin] [$b xMax] [$b yMax]] "	"]
 foreach term [$inst getITerms] {
  if {[[$term getMTerm] getSigType] ni {POWER GROUND}} {continue}
  set net [$term getNet];if {$net ne "NULL"} {set net [$net getName]}
  puts $f [join [list PG [$inst getName] [[$term getMTerm] getName] $net] "	"]
 }
}
set bounds [list 958.745 753.355 960.815 755.425]
foreach inst [$block getInsts] {
 set b [$inst getBBox];lassign $bounds x1 y1 x2 y2
 if {[$b xMin]>$x2*$dbu || [$b xMax]<$x1*$dbu || [$b yMin]>$y2*$dbu || [$b yMax]<$y1*$dbu} {continue}
 set group [$inst getGroup];if {$group ne "NULL"} {set group [$group getName]}
 puts $f [join [list current 71 [$inst getName] [[$inst getMaster] getName] [$inst getLocation] [$inst getOrient] [$inst getPlacementStatus] $group [$b xMin] [$b yMin] [$b xMax] [$b yMax]] "	"]
 foreach term [$inst getITerms] {
  if {[[$term getMTerm] getSigType] ni {POWER GROUND}} {continue}
  set net [$term getNet];if {$net ne "NULL"} {set net [$net getName]}
  puts $f [join [list PG [$inst getName] [[$term getMTerm] getName] $net] "	"]
 }
}
set bounds [list 959.315 753.355 961.385 755.425]
foreach inst [$block getInsts] {
 set b [$inst getBBox];lassign $bounds x1 y1 x2 y2
 if {[$b xMin]>$x2*$dbu || [$b xMax]<$x1*$dbu || [$b yMin]>$y2*$dbu || [$b yMax]<$y1*$dbu} {continue}
 set group [$inst getGroup];if {$group ne "NULL"} {set group [$group getName]}
 puts $f [join [list current 72 [$inst getName] [[$inst getMaster] getName] [$inst getLocation] [$inst getOrient] [$inst getPlacementStatus] $group [$b xMin] [$b yMin] [$b xMax] [$b yMax]] "	"]
 foreach term [$inst getITerms] {
  if {[[$term getMTerm] getSigType] ni {POWER GROUND}} {continue}
  set net [$term getNet];if {$net ne "NULL"} {set net [$net getName]}
  puts $f [join [list PG [$inst getName] [[$term getMTerm] getName] $net] "	"]
 }
}
set bounds [list 346.945 235.775 348.955 237.845]
foreach inst [$block getInsts] {
 set b [$inst getBBox];lassign $bounds x1 y1 x2 y2
 if {[$b xMin]>$x2*$dbu || [$b xMax]<$x1*$dbu || [$b yMin]>$y2*$dbu || [$b yMax]<$y1*$dbu} {continue}
 set group [$inst getGroup];if {$group ne "NULL"} {set group [$group getName]}
 puts $f [join [list current 73 [$inst getName] [[$inst getMaster] getName] [$inst getLocation] [$inst getOrient] [$inst getPlacementStatus] $group [$b xMin] [$b yMin] [$b xMax] [$b yMax]] "	"]
 foreach term [$inst getITerms] {
  if {[[$term getMTerm] getSigType] ni {POWER GROUND}} {continue}
  set net [$term getNet];if {$net ne "NULL"} {set net [$net getName]}
  puts $f [join [list PG [$inst getName] [[$term getMTerm] getName] $net] "	"]
 }
}
set bounds [list 346.955 235.775 349.015 237.845]
foreach inst [$block getInsts] {
 set b [$inst getBBox];lassign $bounds x1 y1 x2 y2
 if {[$b xMin]>$x2*$dbu || [$b xMax]<$x1*$dbu || [$b yMin]>$y2*$dbu || [$b yMax]<$y1*$dbu} {continue}
 set group [$inst getGroup];if {$group ne "NULL"} {set group [$group getName]}
 puts $f [join [list current 74 [$inst getName] [[$inst getMaster] getName] [$inst getLocation] [$inst getOrient] [$inst getPlacementStatus] $group [$b xMin] [$b yMin] [$b xMax] [$b yMax]] "	"]
 foreach term [$inst getITerms] {
  if {[[$term getMTerm] getSigType] ni {POWER GROUND}} {continue}
  set net [$term getNet];if {$net ne "NULL"} {set net [$net getName]}
  puts $f [join [list PG [$inst getName] [[$term getMTerm] getName] $net] "	"]
 }
}
set bounds [list 347.515 235.775 349.585 237.845]
foreach inst [$block getInsts] {
 set b [$inst getBBox];lassign $bounds x1 y1 x2 y2
 if {[$b xMin]>$x2*$dbu || [$b xMax]<$x1*$dbu || [$b yMin]>$y2*$dbu || [$b yMax]<$y1*$dbu} {continue}
 set group [$inst getGroup];if {$group ne "NULL"} {set group [$group getName]}
 puts $f [join [list current 75 [$inst getName] [[$inst getMaster] getName] [$inst getLocation] [$inst getOrient] [$inst getPlacementStatus] $group [$b xMin] [$b yMin] [$b xMax] [$b yMax]] "	"]
 foreach term [$inst getITerms] {
  if {[[$term getMTerm] getSigType] ni {POWER GROUND}} {continue}
  set net [$term getNet];if {$net ne "NULL"} {set net [$net getName]}
  puts $f [join [list PG [$inst getName] [[$term getMTerm] getName] $net] "	"]
 }
}
set bounds [list 422.36 146.175 424.43 148.245]
foreach inst [$block getInsts] {
 set b [$inst getBBox];lassign $bounds x1 y1 x2 y2
 if {[$b xMin]>$x2*$dbu || [$b xMax]<$x1*$dbu || [$b yMin]>$y2*$dbu || [$b yMax]<$y1*$dbu} {continue}
 set group [$inst getGroup];if {$group ne "NULL"} {set group [$group getName]}
 puts $f [join [list current 76 [$inst getName] [[$inst getMaster] getName] [$inst getLocation] [$inst getOrient] [$inst getPlacementStatus] $group [$b xMin] [$b yMin] [$b xMax] [$b yMax]] "	"]
 foreach term [$inst getITerms] {
  if {[[$term getMTerm] getSigType] ni {POWER GROUND}} {continue}
  set net [$term getNet];if {$net ne "NULL"} {set net [$net getName]}
  puts $f [join [list PG [$inst getName] [[$term getMTerm] getName] $net] "	"]
 }
}
set bounds [list 422.735 146.175 424.755 148.245]
foreach inst [$block getInsts] {
 set b [$inst getBBox];lassign $bounds x1 y1 x2 y2
 if {[$b xMin]>$x2*$dbu || [$b xMax]<$x1*$dbu || [$b yMin]>$y2*$dbu || [$b yMax]<$y1*$dbu} {continue}
 set group [$inst getGroup];if {$group ne "NULL"} {set group [$group getName]}
 puts $f [join [list current 77 [$inst getName] [[$inst getMaster] getName] [$inst getLocation] [$inst getOrient] [$inst getPlacementStatus] $group [$b xMin] [$b yMin] [$b xMax] [$b yMax]] "	"]
 foreach term [$inst getITerms] {
  if {[[$term getMTerm] getSigType] ni {POWER GROUND}} {continue}
  set net [$term getNet];if {$net ne "NULL"} {set net [$net getName]}
  puts $f [join [list PG [$inst getName] [[$term getMTerm] getName] $net] "	"]
 }
}
set bounds [list 422.755 146.175 424.805 148.245]
foreach inst [$block getInsts] {
 set b [$inst getBBox];lassign $bounds x1 y1 x2 y2
 if {[$b xMin]>$x2*$dbu || [$b xMax]<$x1*$dbu || [$b yMin]>$y2*$dbu || [$b yMax]<$y1*$dbu} {continue}
 set group [$inst getGroup];if {$group ne "NULL"} {set group [$group getName]}
 puts $f [join [list current 78 [$inst getName] [[$inst getMaster] getName] [$inst getLocation] [$inst getOrient] [$inst getPlacementStatus] $group [$b xMin] [$b yMin] [$b xMax] [$b yMax]] "	"]
 foreach term [$inst getITerms] {
  if {[[$term getMTerm] getSigType] ni {POWER GROUND}} {continue}
  set net [$term getNet];if {$net ne "NULL"} {set net [$net getName]}
  puts $f [join [list PG [$inst getName] [[$term getMTerm] getName] $net] "	"]
 }
}
set bounds [list 423.115 146.175 425.185 148.245]
foreach inst [$block getInsts] {
 set b [$inst getBBox];lassign $bounds x1 y1 x2 y2
 if {[$b xMin]>$x2*$dbu || [$b xMax]<$x1*$dbu || [$b yMin]>$y2*$dbu || [$b yMax]<$y1*$dbu} {continue}
 set group [$inst getGroup];if {$group ne "NULL"} {set group [$group getName]}
 puts $f [join [list current 79 [$inst getName] [[$inst getMaster] getName] [$inst getLocation] [$inst getOrient] [$inst getPlacementStatus] $group [$b xMin] [$b yMin] [$b xMax] [$b yMax]] "	"]
 foreach term [$inst getITerms] {
  if {[[$term getMTerm] getSigType] ni {POWER GROUND}} {continue}
  set net [$term getNet];if {$net ne "NULL"} {set net [$net getName]}
  puts $f [join [list PG [$inst getName] [[$term getMTerm] getName] $net] "	"]
 }
}
set bounds [list 423.495 146.175 425.565 148.245]
foreach inst [$block getInsts] {
 set b [$inst getBBox];lassign $bounds x1 y1 x2 y2
 if {[$b xMin]>$x2*$dbu || [$b xMax]<$x1*$dbu || [$b yMin]>$y2*$dbu || [$b yMax]<$y1*$dbu} {continue}
 set group [$inst getGroup];if {$group ne "NULL"} {set group [$group getName]}
 puts $f [join [list current 80 [$inst getName] [[$inst getMaster] getName] [$inst getLocation] [$inst getOrient] [$inst getPlacementStatus] $group [$b xMin] [$b yMin] [$b xMax] [$b yMax]] "	"]
 foreach term [$inst getITerms] {
  if {[[$term getMTerm] getSigType] ni {POWER GROUND}} {continue}
  set net [$term getNet];if {$net ne "NULL"} {set net [$net getName]}
  puts $f [join [list PG [$inst getName] [[$term getMTerm] getName] $net] "	"]
 }
}
set bounds [list 659.115 994.575 661.185 996.645]
foreach inst [$block getInsts] {
 set b [$inst getBBox];lassign $bounds x1 y1 x2 y2
 if {[$b xMin]>$x2*$dbu || [$b xMax]<$x1*$dbu || [$b yMin]>$y2*$dbu || [$b yMax]<$y1*$dbu} {continue}
 set group [$inst getGroup];if {$group ne "NULL"} {set group [$group getName]}
 puts $f [join [list current 81 [$inst getName] [[$inst getMaster] getName] [$inst getLocation] [$inst getOrient] [$inst getPlacementStatus] $group [$b xMin] [$b yMin] [$b xMax] [$b yMax]] "	"]
 foreach term [$inst getITerms] {
  if {[[$term getMTerm] getSigType] ni {POWER GROUND}} {continue}
  set net [$term getNet];if {$net ne "NULL"} {set net [$net getName]}
  puts $f [join [list PG [$inst getName] [[$term getMTerm] getName] $net] "	"]
 }
}
set bounds [list 659.685 994.575 661.755 996.645]
foreach inst [$block getInsts] {
 set b [$inst getBBox];lassign $bounds x1 y1 x2 y2
 if {[$b xMin]>$x2*$dbu || [$b xMax]<$x1*$dbu || [$b yMin]>$y2*$dbu || [$b yMax]<$y1*$dbu} {continue}
 set group [$inst getGroup];if {$group ne "NULL"} {set group [$group getName]}
 puts $f [join [list current 82 [$inst getName] [[$inst getMaster] getName] [$inst getLocation] [$inst getOrient] [$inst getPlacementStatus] $group [$b xMin] [$b yMin] [$b xMax] [$b yMax]] "	"]
 foreach term [$inst getITerms] {
  if {[[$term getMTerm] getSigType] ni {POWER GROUND}} {continue}
  set net [$term getNet];if {$net ne "NULL"} {set net [$net getName]}
  puts $f [join [list PG [$inst getName] [[$term getMTerm] getName] $net] "	"]
 }
}
set bounds [list 280.81 1117.355 282.88 1119.425]
foreach inst [$block getInsts] {
 set b [$inst getBBox];lassign $bounds x1 y1 x2 y2
 if {[$b xMin]>$x2*$dbu || [$b xMax]<$x1*$dbu || [$b yMin]>$y2*$dbu || [$b yMax]<$y1*$dbu} {continue}
 set group [$inst getGroup];if {$group ne "NULL"} {set group [$group getName]}
 puts $f [join [list current 83 [$inst getName] [[$inst getMaster] getName] [$inst getLocation] [$inst getOrient] [$inst getPlacementStatus] $group [$b xMin] [$b yMin] [$b xMax] [$b yMax]] "	"]
 foreach term [$inst getITerms] {
  if {[[$term getMTerm] getSigType] ni {POWER GROUND}} {continue}
  set net [$term getNet];if {$net ne "NULL"} {set net [$net getName]}
  puts $f [join [list PG [$inst getName] [[$term getMTerm] getName] $net] "	"]
 }
}
set bounds [list 281.185 1117.355 283.255 1119.425]
foreach inst [$block getInsts] {
 set b [$inst getBBox];lassign $bounds x1 y1 x2 y2
 if {[$b xMin]>$x2*$dbu || [$b xMax]<$x1*$dbu || [$b yMin]>$y2*$dbu || [$b yMax]<$y1*$dbu} {continue}
 set group [$inst getGroup];if {$group ne "NULL"} {set group [$group getName]}
 puts $f [join [list current 84 [$inst getName] [[$inst getMaster] getName] [$inst getLocation] [$inst getOrient] [$inst getPlacementStatus] $group [$b xMin] [$b yMin] [$b xMax] [$b yMax]] "	"]
 foreach term [$inst getITerms] {
  if {[[$term getMTerm] getSigType] ni {POWER GROUND}} {continue}
  set net [$term getNet];if {$net ne "NULL"} {set net [$net getName]}
  puts $f [join [list PG [$inst getName] [[$term getMTerm] getName] $net] "	"]
 }
}
set bounds [list 281.565 1117.355 283.635 1119.425]
foreach inst [$block getInsts] {
 set b [$inst getBBox];lassign $bounds x1 y1 x2 y2
 if {[$b xMin]>$x2*$dbu || [$b xMax]<$x1*$dbu || [$b yMin]>$y2*$dbu || [$b yMax]<$y1*$dbu} {continue}
 set group [$inst getGroup];if {$group ne "NULL"} {set group [$group getName]}
 puts $f [join [list current 85 [$inst getName] [[$inst getMaster] getName] [$inst getLocation] [$inst getOrient] [$inst getPlacementStatus] $group [$b xMin] [$b yMin] [$b xMax] [$b yMax]] "	"]
 foreach term [$inst getITerms] {
  if {[[$term getMTerm] getSigType] ni {POWER GROUND}} {continue}
  set net [$term getNet];if {$net ne "NULL"} {set net [$net getName]}
  puts $f [join [list PG [$inst getName] [[$term getMTerm] getName] $net] "	"]
 }
}
set bounds [list 281.945 1117.355 284.015 1119.425]
foreach inst [$block getInsts] {
 set b [$inst getBBox];lassign $bounds x1 y1 x2 y2
 if {[$b xMin]>$x2*$dbu || [$b xMax]<$x1*$dbu || [$b yMin]>$y2*$dbu || [$b yMax]<$y1*$dbu} {continue}
 set group [$inst getGroup];if {$group ne "NULL"} {set group [$group getName]}
 puts $f [join [list current 86 [$inst getName] [[$inst getMaster] getName] [$inst getLocation] [$inst getOrient] [$inst getPlacementStatus] $group [$b xMin] [$b yMin] [$b xMax] [$b yMax]] "	"]
 foreach term [$inst getITerms] {
  if {[[$term getMTerm] getSigType] ni {POWER GROUND}} {continue}
  set net [$term getNet];if {$net ne "NULL"} {set net [$net getName]}
  puts $f [join [list PG [$inst getName] [[$term getMTerm] getName] $net] "	"]
 }
}
set bounds [list 454.85 1117.355 456.92 1119.425]
foreach inst [$block getInsts] {
 set b [$inst getBBox];lassign $bounds x1 y1 x2 y2
 if {[$b xMin]>$x2*$dbu || [$b xMax]<$x1*$dbu || [$b yMin]>$y2*$dbu || [$b yMax]<$y1*$dbu} {continue}
 set group [$inst getGroup];if {$group ne "NULL"} {set group [$group getName]}
 puts $f [join [list current 87 [$inst getName] [[$inst getMaster] getName] [$inst getLocation] [$inst getOrient] [$inst getPlacementStatus] $group [$b xMin] [$b yMin] [$b xMax] [$b yMax]] "	"]
 foreach term [$inst getITerms] {
  if {[[$term getMTerm] getSigType] ni {POWER GROUND}} {continue}
  set net [$term getNet];if {$net ne "NULL"} {set net [$net getName]}
  puts $f [join [list PG [$inst getName] [[$term getMTerm] getName] $net] "	"]
 }
}
close $f
