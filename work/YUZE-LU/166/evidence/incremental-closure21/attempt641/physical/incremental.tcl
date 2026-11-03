set_thread_count 16
read_liberty /OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib
read_db {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-166-r-local-state/attempt596/physical/flow/results/nangate45/r166_1024/base/6_final.odb}
read_sdc {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-166-r-local-state/attempt596/physical/flow/results/nangate45/r166_1024/base/6_final.sdc}
set here {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-166-r-local-state/attempt641/physical}
set block [ord::get_db_block];set dbu [$block getDbUnitsPerMicron]
remove_fillers
source {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-166-r-local-state/attempt641/physical/buffer_locality.tcl}
source {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-166-r-local-state/attempt641/physical/fixed_clock_prepare.tcl}
write_def $here/INCREMENTAL_BEFORE.def
read_guides {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-166-r-local-state/attempt596/physical/flow/results/nangate45/r166_1024/base/route.guide}
set affected [dict create]
foreach name [list {$auto$ff.cc:337:slice$256819/D} {$auto$ff.cc:337:slice$264150/D} {$auto$ff.cc:337:slice$264153/D} {$auto$ff.cc:337:slice$283390/D} {$auto$ff.cc:337:slice$369109/D} {$auto$ff.cc:337:slice$369125/D} {$auto$ff.cc:337:slice$369127/D} {$auto$ff.cc:337:slice$399669/D} {$auto$ff.cc:337:slice$425341/D} {$auto$ff.cc:337:slice$429006/D}] {
 set slash [string last / $name];set inst [$block findInst [string range $name 0 [expr {$slash-1}]]]
 if {$inst eq "NULL"} {error "Measured data endpoint absent"}
 set net [[$inst findITerm D] getNet]
 if {$net eq "NULL" || [$net getSigType] in {CLOCK POWER GROUND}} {error "Measured endpoint is not a data net"}
 dict set affected [$net getName] 1
}
set f [open $here/INCREMENTAL_AFFECTED_NETS.tsv w]
dict for {name unused} $affected {puts $f $name}
close $f
global_route -start_incremental
source {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-166-r-local-state/attempt641/physical/extracted_endpoints.tcl}
# A modified source net cannot retain a stale wire ending at the old D pin.
# Every other source data wire remains available to detailed routing.
dict for {name unused} $affected {
 set net [$block findNet $name];set wire [$net getWire]
 if {$wire ne "NULL"} {odb::dbWire_destroy $wire}
}
global_route -end_incremental
write_guides {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-166-r-local-state/attempt641/physical/flow/results/nangate45/r166_1024/base/route.guide}
write_def $here/INCREMENTAL_AFTER_GRT.def
write_db {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-166-r-local-state/attempt641/physical/flow/results/nangate45/r166_1024/base/5_1_grt.odb}
write_sdc {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-166-r-local-state/attempt641/physical/flow/results/nangate45/r166_1024/base/5_1_grt.sdc}
