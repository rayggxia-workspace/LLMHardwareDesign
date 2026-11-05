read_liberty /OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib
read_db {/public/home/yuzelu/PingyangHuang/issue177-s-p4setup-20261104T054519Z/sealed/p4/flow/results/nangate45/bv1_local_s_p4/base/6_final.odb}
set remove {}
foreach lib [[ord::get_db] getLibs] {
 foreach master [$lib getMasters] {
  set signal 0
  foreach term [$master getMTerms] {if {[$term getSigType] ni {POWER GROUND}} {set signal 1}}
  if {!$signal} {lappend remove [$master getName]}
 }
}
write_verilog -remove_cells $remove {/public/home/yuzelu/PingyangHuang/issue177-s-p4setup-20261104T054519Z/gates/p4/function/physical-functional.v}
