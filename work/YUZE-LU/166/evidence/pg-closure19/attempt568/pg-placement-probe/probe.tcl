set_thread_count 16
read_liberty /OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib
read_db {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-166-r-local-state/attempt539/physical/flow/results/nangate45/r166_1024/base/6_final.odb}
set block [ord::get_db_block]
remove_fillers
set before [dict create]
foreach inst [$block getInsts] {dict set before [$inst getName] [list [[$inst getMaster] getName] [$inst getLocation] [$inst getOrient]]}
set site [[lindex [$block getRows] 0] getSite];set pitch [$site getWidth]
set f [open moves.tsv w]
set name {r166_hold_endpoint_extracted_0000525029}
set inst [$block findInst $name]
if {$inst eq "NULL" || [[$inst getMaster] getName] ne {CLKBUF_X1} || [$inst getLocation] ne {176320 2234400} || [$inst getOrient] ne {MX}} {error "Measured data buffer differs"}
lassign [$inst getLocation] x y
$inst setLocation [expr {$x+8*$pitch}] $y
puts $f [join [list $name [[$inst getMaster] getName] $x $y {*}[$inst getLocation] [$inst getOrient] $pitch] "	"]
set name {r166_hold_endpoint_extracted_0000625030}
set inst [$block findInst $name]
if {$inst eq "NULL" || [[$inst getMaster] getName] ne {CLKBUF_X1} || [$inst getLocation] ne {175180 2234400} || [$inst getOrient] ne {MX}} {error "Measured data buffer differs"}
lassign [$inst getLocation] x y
$inst setLocation [expr {$x+8*$pitch}] $y
puts $f [join [list $name [[$inst getMaster] getName] $x $y {*}[$inst getLocation] [$inst getOrient] $pitch] "	"]
set name {r166_hold_endpoint_extracted_0001125035}
set inst [$block findInst $name]
if {$inst eq "NULL" || [[$inst getMaster] getName] ne {CLKBUF_X1} || [$inst getLocation] ne {320720 2713200} || [$inst getOrient] ne {R0}} {error "Measured data buffer differs"}
lassign [$inst getLocation] x y
$inst setLocation [expr {$x+8*$pitch}] $y
puts $f [join [list $name [[$inst getMaster] getName] $x $y {*}[$inst getLocation] [$inst getOrient] $pitch] "	"]
set name {r166_hold_endpoint_extracted_0001225036}
set inst [$block findInst $name]
if {$inst eq "NULL" || [[$inst getMaster] getName] ne {CLKBUF_X1} || [$inst getLocation] ne {319580 2713200} || [$inst getOrient] ne {R0}} {error "Measured data buffer differs"}
lassign [$inst getLocation] x y
$inst setLocation [expr {$x+8*$pitch}] $y
puts $f [join [list $name [[$inst getMaster] getName] $x $y {*}[$inst getLocation] [$inst getOrient] $pitch] "	"]
close $f
check_placement -verbose
foreach inst [$block getInsts] {
 set name [$inst getName];set old [dict get $before $name];set now [list [[$inst getMaster] getName] [$inst getLocation] [$inst getOrient]]
 if {$old ne $now && [lsearch -exact {r166_hold_endpoint_extracted_0000525029 r166_hold_endpoint_extracted_0000625030 r166_hold_endpoint_extracted_0001125035 r166_hold_endpoint_extracted_0001225036} $name]<0} {error "An unselected original cell changed"}
}
set removed 0
foreach net [$block getNets] {
 if {[$net getSigType] in {CLOCK POWER GROUND}} {continue}
 set wire [$net getWire];if {$wire ne "NULL"} {odb::dbWire_destroy $wire;incr removed}
}
puts "R166_DIAGNOSTIC_DATA_ROUTES_REMOVED=$removed; no_data_route_qualification=1"
filler_placement {FILLCELL_X32 FILLCELL_X16 FILLCELL_X8 FILLCELL_X4 FILLCELL_X2 FILLCELL_X1}
add_global_connection -net VDD -inst_pattern .* -pin_pattern VDD -power
add_global_connection -net VSS -inst_pattern .* -pin_pattern VSS -ground
global_connect
set failed 0
foreach net {VDD VSS} {
 set code [catch {check_power_grid -net $net -error_file ${net}.rpt} message]
 puts "R166_PG_PLACEMENT_CHECK; net=$net; code=$code; message=$message"
 if {$code} {set failed 1}
}
write_def candidate.def
write_db candidate.odb
if {$failed} {error "Original PG connectivity check failed for diagnostic placement"}
