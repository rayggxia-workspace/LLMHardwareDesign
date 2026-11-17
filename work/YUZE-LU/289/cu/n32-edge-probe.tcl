read_db /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/runs/U-v6-ctsdelay-x8-seed0/flow/results/nangate45/u-overlay-current/base/5_1_grt.odb
set b [ord::get_db_block]
set out [open /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/n32-edge-geometry.tsv w]
foreach i [$b getInsts] {
 if {[$i getName] ne "datapath.n32"} {continue}
 puts $out "MACRO [$i getLocation] [$i getOrient]"
 foreach it [$i getITerms] {
  foreach g [$it getGeometries] {
   lassign $g layer r
   if {[$r yMin]>1993000 && [$r yMin]<1999000} {puts $out [join [list PIN [[$it getMTerm] getName] [$layer getName] [$r xMin] [$r yMin] [$r xMax] [$r yMax]] "\t"]}
  }
 }
}
foreach name {VDD VSS} {
 foreach sw [[$b findNet $name] getSWires] {
  foreach r [$sw getWires] {
   if {[$r yMax]<1995000 || [$r yMin]>1999000 || [$r xMax]<340000 || [$r xMin]>720000} {continue}
   set layer VIA
   if {![$r isVia]} {set layer [[$r getTechLayer] getName]}
   puts $out [join [list PG $name $layer [$r xMin] [$r yMin] [$r xMax] [$r yMax]] "\t"]
  }
 }
}
close $out
