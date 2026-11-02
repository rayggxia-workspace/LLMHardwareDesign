read_lef /OpenROAD-flow-scripts/flow/platforms/nangate45/lef/NangateOpenCellLibrary.tech.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/nangate45/lef/NangateOpenCellLibrary.macro.mod.lef
read_lef /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-155/m3-abstract-002/bank.lef
read_def /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-155/pin-tracks-003/cts.def
set_thread_count 2
set block [ord::get_db_block]
set tech [[ord::get_db] getTech]

set xs {};set ys {}
foreach inst [$block getInsts] {
 if {[[$inst getMaster] getName] ne "s_sram_256x128_freepdk45"} {continue}
 lassign [$inst getLocation] dx dy
 foreach term [[$inst getMaster] getMTerms] {
  if {[$term getSigType] ne "SIGNAL" && [$term getSigType] ne "CLOCK"} {continue}
  foreach pin [$term getMPins] {foreach box [$pin getGeometry] {
   if {[[$box getTechLayer] getName] ne "metal3"} {continue}
   lappend xs [expr {int(round((([$box xMin]+[$box xMax])/2.0+$dx)/10.0))*10}]
   lappend ys [expr {int(round((([$box yMin]+[$box yMax])/2.0+$dy)/10.0))*10}]
  }}
 }
}
set xs [lsort -integer -unique $xs];set ys [lsort -integer -unique $ys]
set grid [$block findTrackGrid [$tech findLayer metal3]]
foreach value $xs {$grid addGridPatternX $value 1 10}
set grid [$block findTrackGrid [$tech findLayer metal4]]
foreach value $xs {$grid addGridPatternX $value 1 10}
pin_access -via_in_pin_bottom_layer metal10 -via_in_pin_top_layer metal10
exit
