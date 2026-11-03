set here {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-166-r-local-state/attempt715/short-hook-probe/five}
set block [ord::get_db_block]
set ::r166_short_obstructions {}
set ::r166_original_obstructions [llength [$block getObstructions]]
set f [open $here/SHORT_TEMP_OBSTRUCTIONS.tsv w]
set dbu [$block getDbUnitsPerMicron]
set layer [[ord::get_db_tech] findLayer {metal2}]
if {$layer eq "NULL"} {error "Short layer absent"}
set rect [list [expr {round(547.8800*$dbu)}] [expr {round(1103.5150*$dbu)}] [expr {round(548.2300*$dbu)}] [expr {round(1103.8650*$dbu)}]]
set obs [odb::dbObstruction_create $block $layer {*}$rect]
if {$obs eq "NULL"} {error "Keepout creation failed"}
lappend ::r166_short_obstructions [list $obs $layer $rect]
puts $f "[$obs getId]	[$layer getName]	$rect"
set layer [[ord::get_db_tech] findLayer {metal2}]
if {$layer eq "NULL"} {error "Short layer absent"}
set rect [list [expr {round(547.8800*$dbu)}] [expr {round(1103.5150*$dbu)}] [expr {round(548.2300*$dbu)}] [expr {round(1104.1800*$dbu)}]]
set obs [odb::dbObstruction_create $block $layer {*}$rect]
if {$obs eq "NULL"} {error "Keepout creation failed"}
lappend ::r166_short_obstructions [list $obs $layer $rect]
puts $f "[$obs getId]	[$layer getName]	$rect"
close $f
if {[llength [$block getObstructions]]!=$::r166_original_obstructions+[llength $::r166_short_obstructions]} {error "Unexpected obstruction changes"}
