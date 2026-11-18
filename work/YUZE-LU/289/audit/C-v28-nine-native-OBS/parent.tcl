read_db /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/C-v28-nine-net-combined-v1/patched.odb
set b [ord::get_db_block]
set tech [[ord::get_db] getTech]
set f [open parent-layers.tsv w]
foreach l [$tech getLayers] {puts $f "[$l getName]\t[$l getWidth]"};close $f
set f [open parent-vias.tsv w]
foreach v [concat [$tech getVias] [$b getVias]] {foreach box [$v getBoxes] {puts $f "[$v getName]\t[[$box getTechLayer] getName]\t[$box xMin]\t[$box yMin]\t[$box xMax]\t[$box yMax]"}};close $f
set ri {}
foreach inst [$b getInsts] {if {[[$inst getMaster] getName] eq "r_stream_local"} {lappend ri $inst}}
if {[llength $ri]!=1} {error "Nonunique actual R macro"}
set inst [lindex $ri 0]
if {[$inst getOrient] ne "R0" || [$inst getOrigin] ne "144000 144000"} {error "R transform mismatch"}
lassign [$inst getOrigin] ox oy
set f [open parent-obs.tsv w]
foreach box [[$inst getMaster] getObstructions] {if {[[$box getTechLayer] getName] eq "metal9"} {puts $f "[expr {$ox+[$box xMin]}]\t[expr {$oy+[$box yMin]}]\t[expr {$ox+[$box xMax]}]\t[expr {$oy+[$box yMax]}]"}}
close $f
