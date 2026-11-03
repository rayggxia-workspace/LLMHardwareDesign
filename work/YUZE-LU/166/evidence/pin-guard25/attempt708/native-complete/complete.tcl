set_thread_count 16
read_lef {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-166-r-local-state/attempt708/native-complete/bridge.lef}
read_lef {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-166-r-local-state/attempt708/native-complete/bridge_1.lef}
read_def {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-166-r-local-state/attempt708/native-complete/bridge.def}

set b [ord::get_db_block];set die [$b getDieArea];set g [$b getGCellGrid]
if {[$die xMin]!=0 || [$die yMin]!=0 || [$die xMax]!=[$die yMax]} {error "Unexpected die"}
write_def before.def
set gx {};set gy {}
for {set i 0} {$i<[$g getNumGridPatternsX]} {incr i} {lappend gx [$g getGridPatternX $i]}
for {set i 0} {$i<[$g getNumGridPatternsY]} {incr i} {lappend gy [$g getGridPatternY $i]}
$g resetGrid
$g addGridPatternX 0 2 [$die xMax]
$g addGridPatternY 0 2 [$die yMax]
if {[$g getGridX] ne [list 0 [$die xMax]] || [$g getGridY] ne [list 0 [$die yMax]]} {error "Incomplete check coverage"}
write_def complete-before.def
drt::check_drc_cmd complete.rpt 0 0 0 0 complete_die
write_def complete-after.def
$g resetGrid
foreach row $gx {lassign $row origin count step;$g addGridPatternX $origin $count $step}
foreach row $gy {lassign $row origin count step;$g addGridPatternY $origin $count $step}
write_def after.def
puts COMPLETE_NATIVE_DIAGNOSTIC_FINISHED
