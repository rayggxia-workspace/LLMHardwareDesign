read_liberty {/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib}
read_liberty {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-155/bank-views-011/generation/bank/s_sram_256x128_freepdk45_TT_1p1V_25C.lib}
read_db {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-155/physical-033/implementation/flow/results/nangate45/s_sram_155/base/6_final.odb}
set remove {}
foreach lib [[ord::get_db] getLibs] {foreach master [$lib getMasters] {set signal 0; foreach term [$master getMTerms] {if {[$term getSigType] ni {POWER GROUND}} {set signal 1}}; if {!$signal} {lappend remove [$master getName]}}}
write_verilog -remove_cells $remove {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-155/formal-030/proof/full-final.v}
