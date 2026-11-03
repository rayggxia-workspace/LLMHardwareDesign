set_thread_count 16
read_liberty /OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib
read_db {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-166-r-local-state/attempt658/physical/flow/results/nangate45/r166_1024/base/6_final.odb}
read_sdc {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-166-r-local-state/attempt658/physical/flow/results/nangate45/r166_1024/base/6_final.sdc}
set here {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-166-r-local-state/attempt678/physical}
set block [ord::get_db_block]
remove_fillers
source {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-166-r-local-state/attempt678/physical/fixed_clock_prepare.tcl}
set data [dict create]
set f [open $here/SHORT_NET_CLASSES.tsv w]
foreach pair [list [list {clknet_leaf_884_clk} {net17426}] [list {$abc$862551$new_n312309} {clknet_leaf_905_clk}] [list {$abc$862551$new_n312309} {clknet_leaf_905_clk}] [list {clknet_leaf_819_clk} {net14774}] [list {clknet_leaf_819_clk} {net14774}]] {
 set clocks 0;set signals 0
 foreach name $pair {
  set net [$block findNet $name]
  if {$net eq "NULL"} {error "Measured short net missing"}
  set kind [$net getSigType];puts $f "$name	$kind"
  if {$kind eq "CLOCK"} {incr clocks} elseif {$kind eq "SIGNAL"} {incr signals;dict set data $name 1} else {error "Short is not data-clock"}
 }
 if {$clocks!=1 || $signals!=1} {error "Expected one data and one fixed clock net"}
}
close $f
set f [open $here/SHORT_DATA_NETS.tsv w]
dict for {name unused} $data {
 set net [$block findNet $name];set wire [$net getWire]
 if {$wire eq "NULL"} {error "Measured data wire absent"}
 odb::dbWire_destroy $wire;puts $f $name
}
close $f
write_db {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-166-r-local-state/attempt678/physical/flow/results/nangate45/r166_1024/base/5_1_grt.odb}
write_sdc {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-166-r-local-state/attempt678/physical/flow/results/nangate45/r166_1024/base/5_1_grt.sdc}
