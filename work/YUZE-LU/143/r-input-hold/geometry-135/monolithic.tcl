set_thread_count 16
read_db {/public/home/yuzelu/project-circuit/llm_routing_analysis/worktrees/issue143-seven-block-v2-20261030/outputs/129/candidate.odb}

set b [ord::get_db_block]
set die [$b getDieArea]
if {[$b getDbUnitsPerMicron]!=2000 || [$die xMin]!=0 || [$die yMin]!=0 || [$die xMax]!=6000000 || [$die yMax]!=6000000} {error "Unexpected complete die"}
write_def before.def
set g [$b getGCellGrid]
if {[$g getNumGridPatternsX]!=1 || [$g getNumGridPatternsY]!=1} {error "Unexpected source grid"}
$g resetGrid
$g addGridPatternX 0 2 6000000
$g addGridPatternY 0 2 6000000
if {[$g getGridX] ne {0 6000000} || [$g getGridY] ne {0 6000000}} {error "Whole-die grid readback failed"}
write_def grid-only.def
drt::check_drc_cmd native-monolithic-drc.rpt 0 0 0 0 native_monolithic_drc
puts WHOLE_DIE_NATIVE_DRC_COMPLETE
