read_liberty /OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib
read_db {/public/home/yuzelu/PingyangHuang/issue177-s-holdeco-20261104T040639Z/sealed/n5/flow/results/nangate45/bv1_local_s_n5/base/6_final.odb}
set remove {}
foreach lib [[ord::get_db] getLibs] {
 foreach master [$lib getMasters] {
  set signal 0
  foreach term [$master getMTerms] {if {[$term getSigType] ni {POWER GROUND}} {set signal 1}}
  if {!$signal} {lappend remove [$master getName]}
 }
}
write_verilog -remove_cells $remove {/public/home/yuzelu/PingyangHuang/issue177-s-holdeco-20261104T040639Z/gates/n5/function/physical-functional.v}
