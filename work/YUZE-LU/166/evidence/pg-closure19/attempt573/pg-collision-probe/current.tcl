set_thread_count 16
set f [open cells_current.tsv w]
read_db {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-166-r-local-state/attempt551/physical/flow/results/nangate45/r166_1024/base/6_final.odb}
set block [ord::get_db_block]
set dbu [$block getDbUnitsPerMicron]
set bounds [list 116.65 1440.755 118.675 1442.825]
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
set bounds [list 117.405 1440.755 119.475 1442.825]
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
set bounds [list 116.675 1440.755 118.72 1442.825]
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
set bounds [list 117.785 1440.755 119.855 1442.825]
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
set bounds [list 117.025 1440.755 119.095 1442.825]
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
set bounds [list 156.74 1687.155 158.81 1689.225]
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
set bounds [list 157.115 1687.155 159.185 1689.225]
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
set bounds [list 157.115 1687.155 159.185 1689.225]
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
set bounds [list 434.515 1647.955 436.585 1650.025]
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
set bounds [list 434.155 1647.955 436.205 1650.025]
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
set bounds [list 433.76 1647.955 435.83 1650.025]
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
set bounds [list 434.135 1647.955 436.155 1650.025]
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
set bounds [list 434.515 1647.955 436.585 1650.025]
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
set bounds [list 1736.02 1561.155 1738.09 1563.225]
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
set bounds [list 1736.775 1561.155 1738.845 1563.225]
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
set bounds [list 1736.395 1561.155 1738.465 1563.225]
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
set bounds [list 1737.155 1561.155 1739.225 1563.225]
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
set bounds [list 471.375 147.155 473.445 149.225]
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
set bounds [list 471.755 147.155 473.825 149.225]
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
set bounds [list 472.135 147.155 474.205 149.225]
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
close $f
