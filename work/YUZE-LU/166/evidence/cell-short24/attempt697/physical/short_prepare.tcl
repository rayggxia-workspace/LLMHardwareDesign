set_thread_count 16
read_liberty /OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib
read_db {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-166-r-local-state/attempt658/physical/flow/results/nangate45/r166_1024/base/6_final.odb}
read_sdc {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-166-r-local-state/attempt658/physical/flow/results/nangate45/r166_1024/base/6_final.sdc}
set here {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-166-r-local-state/attempt697/physical}
set block [ord::get_db_block]
remove_fillers
source {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-166-r-local-state/attempt697/physical/fixed_clock_prepare.tcl}
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
read_guides {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-166-r-local-state/attempt658/physical/flow/results/nangate45/r166_1024/base/route.guide}
set before [dict create]
foreach inst [$block getInsts] {dict set before [$inst getName] [list [[$inst getMaster] getName] [$inst getLocation] [$inst getOrient]]}
global_route -start_incremental
set moved [dict create]
set f [open $here/SHORT_MOVED_CELL_NETS.tsv w]
set inst [$block findInst {$abc$862551$auto$blifparse.cc:397:parse_blif$1000769}]
if {$inst eq "NULL" || [[$inst getMaster] getName] ne {AOI21_X1} || [$inst getLocation] ne {1109220 2212000} || [$inst getOrient] ne {MX}} {error "Measured cell placement source differs"}
$inst setPlacementStatus PLACED
$inst setLocation 1094780 2206400
$inst setPlacementStatus LOCKED
dict set moved {$abc$862551$auto$blifparse.cc:397:parse_blif$1000769} 1
foreach term [$inst getITerms] {
 set net [$term getNet];if {$net eq "NULL"} {continue}
 set kind [$net getSigType]
 if {$kind in {POWER GROUND}} {continue}
 if {$kind ne "SIGNAL"} {error "Measured combinational cell has a clock connection"}
 dict set data [$net getName] 1
 puts $f [join [list [$inst getName] [$net getName] $kind] "	"]
}
set inst [$block findInst {$abc$862551$auto$blifparse.cc:397:parse_blif$971512}]
if {$inst eq "NULL" || [[$inst getMaster] getName] ne {NOR4_X1} || [$inst getLocation] ne {1108840 2273600} || [$inst getOrient] ne {MX}} {error "Measured cell placement source differs"}
$inst setPlacementStatus PLACED
$inst setLocation 1094400 2268000
$inst setPlacementStatus LOCKED
dict set moved {$abc$862551$auto$blifparse.cc:397:parse_blif$971512} 1
foreach term [$inst getITerms] {
 set net [$term getNet];if {$net eq "NULL"} {continue}
 set kind [$net getSigType]
 if {$kind in {POWER GROUND}} {continue}
 if {$kind ne "SIGNAL"} {error "Measured combinational cell has a clock connection"}
 dict set data [$net getName] 1
 puts $f [join [list [$inst getName] [$net getName] $kind] "	"]
}
set inst [$block findInst {wire17425}]
if {$inst eq "NULL" || [[$inst getMaster] getName] ne {BUF_X4} || [$inst getLocation] ne {1101240 2273600} || [$inst getOrient] ne {MX}} {error "Measured cell placement source differs"}
$inst setPlacementStatus PLACED
$inst setLocation 1091740 2268000
$inst setPlacementStatus LOCKED
dict set moved {wire17425} 1
foreach term [$inst getITerms] {
 set net [$term getNet];if {$net eq "NULL"} {continue}
 set kind [$net getSigType]
 if {$kind in {POWER GROUND}} {continue}
 if {$kind ne "SIGNAL"} {error "Measured combinational cell has a clock connection"}
 dict set data [$net getName] 1
 puts $f [join [list [$inst getName] [$net getName] $kind] "	"]
}
set net [$block findNet {$abc$862551$new_n283097}]
if {$net eq "NULL" || [$net getSigType] ne "SIGNAL" || [$net getWire] eq "NULL"} {error "Measured additional PG wire is not routed data"}
dict set data {$abc$862551$new_n283097} 1
set net [$block findNet {net17317}]
if {$net eq "NULL" || [$net getSigType] ne "SIGNAL" || [$net getWire] eq "NULL"} {error "Measured additional PG wire is not routed data"}
dict set data {net17317} 1
close $f
set f [open $here/SHORT_DATA_NETS.tsv w]
dict for {name unused} $data {
 set net [$block findNet $name];set wire [$net getWire]
 if {$wire eq "NULL"} {error "Measured data wire absent"}
 odb::dbWire_destroy $wire;puts $f $name
}
close $f
global_route -end_incremental
foreach inst [$block getInsts] {
 set name [$inst getName]
 if {![dict exists $moved $name] && [dict get $before $name] ne [list [[$inst getMaster] getName] [$inst getLocation] [$inst getOrient]]} {error "An unselected original cell changed"}
}
write_guides {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-166-r-local-state/attempt697/physical/flow/results/nangate45/r166_1024/base/route.guide}
write_db {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-166-r-local-state/attempt697/physical/flow/results/nangate45/r166_1024/base/5_1_grt.odb}
write_sdc {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-166-r-local-state/attempt697/physical/flow/results/nangate45/r166_1024/base/5_1_grt.sdc}
