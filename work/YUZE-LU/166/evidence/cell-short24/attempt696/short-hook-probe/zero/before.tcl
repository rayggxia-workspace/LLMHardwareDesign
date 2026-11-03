set here {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-166-r-local-state/attempt696/short-hook-probe/zero}
set block [ord::get_db_block]
set ::r166_short_obstructions {}
set ::r166_original_obstructions [llength [$block getObstructions]]
set f [open $here/SHORT_TEMP_OBSTRUCTIONS.tsv w]
set dbu [$block getDbUnitsPerMicron]
close $f
if {[llength [$block getObstructions]]!=$::r166_original_obstructions+[llength $::r166_short_obstructions]} {error "Unexpected obstruction changes"}
