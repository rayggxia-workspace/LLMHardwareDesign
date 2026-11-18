set root /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117
read_db $root/cu/runs/U-v7-macropdn-x8-seed0/flow/results/nangate45/u-overlay-current/base/6_final.odb
set b [ord::get_db_block]
set f [open $root/u-physical/pg.tsv w]
foreach rail {VDD VSS} {
 foreach sw [[$b findNet $rail] getSWires] {
  foreach box [$sw getWires] {
   if {[$box isVia]} {
    set via [$box getTechVia]
    if {$via eq "NULL"} {set via [$box getBlockVia]}
    lassign [$box getViaXY] x y
    foreach shape [$via getBoxes] {
     set layer [[$shape getTechLayer] getName]
     if {$layer ni {metal7 metal8 metal9 metal10 via7 via8 via9}} {continue}
     puts $f "$rail\tPGVIA:[$via getName]:$x:$y\t$layer\t[expr {[$shape xMin]+$x}]\t[expr {[$shape yMin]+$y}]\t[expr {[$shape xMax]+$x}]\t[expr {[$shape yMax]+$y}]"
    }
   } else {
    set layer [[$box getTechLayer] getName]
    if {$layer ni {metal7 metal8 metal9 metal10}} {continue}
    puts $f "$rail\tPGWIRE\t$layer\t[$box xMin]\t[$box yMin]\t[$box xMax]\t[$box yMax]"
   }
  }
 }
}
close $f
puts U_PG_GEOMETRY_COMPLETE
