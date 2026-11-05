read_liberty /OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib
read_db {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/r256-native-353/3530/gates/sealed/flow/results/nangate45/bv1_control_reset_distribution_r53/base/6_final.odb}
set remove {}
foreach lib [[ord::get_db] getLibs] {
 foreach master [$lib getMasters] {
  set signal 0
  foreach term [$master getMTerms] {if {[$term getSigType] ni {POWER GROUND}} {set signal 1}}
  if {!$signal} {lappend remove [$master getName]}
 }
}
write_verilog -remove_cells $remove {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/r256-native-353/3530/gates/function/physical-functional.v}
