set here {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-166-r-local-state/attempt718/physical}
write_def {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-166-r-local-state/attempt718/physical/CLOCK_pre-restore.def}
puts [exec python3 {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-166-r-local-state/attempt718/project/experiments/r_local_state/fixed_clock_routes.py} precheck --physical {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-166-r-local-state/attempt718/physical} --def {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-166-r-local-state/attempt718/physical/CLOCK_pre-restore.def}]
read_def -floorplan_initialize {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-166-r-local-state/attempt718/physical/CLOCK_FIXED.def}
write_def {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-166-r-local-state/attempt718/physical/CLOCK_before-detail.def}
puts [exec python3 {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-166-r-local-state/attempt718/project/experiments/r_local_state/fixed_clock_routes.py} audit --physical {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-166-r-local-state/attempt718/physical} --def {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-166-r-local-state/attempt718/physical/CLOCK_before-detail.def} --phase before-detail]
filler_placement {FILLCELL_X32 FILLCELL_X16 FILLCELL_X8 FILLCELL_X4 FILLCELL_X2 FILLCELL_X1}
add_global_connection -net VDD -inst_pattern .* -pin_pattern VDD -power
add_global_connection -net VSS -inst_pattern .* -pin_pattern VSS -ground
global_connect
check_placement -verbose
write_db {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-166-r-local-state/attempt718/physical/CLOCK_POST_RESTORE.odb}
set f [open {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-166-r-local-state/attempt718/physical/PG_PRE_ROUTE.tsv} w];set pg_failed 0
foreach supply {VDD VSS} {
 set code [catch {check_power_grid -net $supply -error_file $here/${supply}-pre-route.rpt} value]
 set valid [expr {$code==0 && [string is boolean -strict $value] && $value}]
 puts $f "$supply\t$code\t$valid";puts "R166_PRE_ROUTE_PG; supply=$supply; code=$code; valid=$valid"
 if {!$valid} {set pg_failed 1}
}
close $f
if {$pg_failed} {error "Original both-supply PG component failed before DRT; immutable checkpoint retained"}
remove_fillers
set here {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-166-r-local-state/attempt718/physical}
set block [ord::get_db_block]
set ::r166_short_obstructions {}
set ::r166_original_obstructions [llength [$block getObstructions]]
set f [open $here/SHORT_TEMP_OBSTRUCTIONS.tsv w]
set dbu [$block getDbUnitsPerMicron]
close $f
if {[llength [$block getObstructions]]!=$::r166_original_obstructions+[llength $::r166_short_obstructions]} {error "Unexpected obstruction changes"}
