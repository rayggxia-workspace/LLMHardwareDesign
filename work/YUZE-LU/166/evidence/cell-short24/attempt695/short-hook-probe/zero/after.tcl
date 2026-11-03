set here {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-166-r-local-state/attempt695/short-hook-probe/zero}
set block [ord::get_db_block]
foreach row $::r166_short_obstructions {
 lassign $row obs layer rect
 set box [$obs getBBox]
 if {[$obs getTechLayer] ne $layer || [list [$box xMin] [$box yMin] [$box xMax] [$box yMax]] ne $rect} {error "Temporary keepout identity changed"}
 odb::dbObstruction_destroy $obs
}
if {[llength [$block getObstructions]]!=$::r166_original_obstructions} {error "Temporary keepout removal incomplete"}
set f [open $here/SHORT_TEMP_OBSTRUCTIONS_REMOVED.tsv w]
puts $f "[llength $::r166_short_obstructions]	$::r166_original_obstructions	[llength [$block getObstructions]]"
close $f
