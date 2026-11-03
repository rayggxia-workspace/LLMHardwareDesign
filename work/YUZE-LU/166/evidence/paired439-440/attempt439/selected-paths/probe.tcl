set_thread_count 16
read_liberty /OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib
read_db {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-166-r-local-state/attempt348/physical/flow/results/nangate45/r166_1024/base/6_final.odb}
read_sdc {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-166-r-local-state/attempt348/physical/flow/results/nangate45/r166_1024/base/6_final.sdc}
read_spef {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-166-r-local-state/attempt348/physical/flow/results/nangate45/r166_1024/base/6_final.spef}
set_propagated_clock [all_clocks]
sta::find_timing
set f [open selected-min.tsv w]
set r [open selected-min.rpt w];close $r
set start {$auto$ff.cc:337:slice$258622/Q}
set end {$auto$ff.cc:337:slice$256817/D}
set sp [get_pins [list $start]];set ep [get_pins [list $end]]
if {[llength $sp]!=1 || [llength $ep]!=1} {error "Missing paired data path $start -> $end"}
set paths [find_timing_paths -from $sp -to $ep -path_delay min -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained paired path $start -> $end"}
puts $f "$start	$end	[get_property [lindex $paths 0] slack]"
report_checks -from $sp -to $ep -path_delay min -group_path_count 1 -endpoint_path_count 1 -digits 9 -format full_clock_expanded >> selected-min.rpt
set start {$auto$ff.cc:337:slice$260696/Q}
set end {$auto$ff.cc:337:slice$256797/D}
set sp [get_pins [list $start]];set ep [get_pins [list $end]]
if {[llength $sp]!=1 || [llength $ep]!=1} {error "Missing paired data path $start -> $end"}
set paths [find_timing_paths -from $sp -to $ep -path_delay min -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained paired path $start -> $end"}
puts $f "$start	$end	[get_property [lindex $paths 0] slack]"
report_checks -from $sp -to $ep -path_delay min -group_path_count 1 -endpoint_path_count 1 -digits 9 -format full_clock_expanded >> selected-min.rpt
set start {$auto$ff.cc:337:slice$271004/Q}
set end {$auto$ff.cc:337:slice$264162/D}
set sp [get_pins [list $start]];set ep [get_pins [list $end]]
if {[llength $sp]!=1 || [llength $ep]!=1} {error "Missing paired data path $start -> $end"}
set paths [find_timing_paths -from $sp -to $ep -path_delay min -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained paired path $start -> $end"}
puts $f "$start	$end	[get_property [lindex $paths 0] slack]"
report_checks -from $sp -to $ep -path_delay min -group_path_count 1 -endpoint_path_count 1 -digits 9 -format full_clock_expanded >> selected-min.rpt
set start {$auto$ff.cc:337:slice$292118/Q}
set end {$auto$ff.cc:337:slice$283400/D}
set sp [get_pins [list $start]];set ep [get_pins [list $end]]
if {[llength $sp]!=1 || [llength $ep]!=1} {error "Missing paired data path $start -> $end"}
set paths [find_timing_paths -from $sp -to $ep -path_delay min -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained paired path $start -> $end"}
puts $f "$start	$end	[get_property [lindex $paths 0] slack]"
report_checks -from $sp -to $ep -path_delay min -group_path_count 1 -endpoint_path_count 1 -digits 9 -format full_clock_expanded >> selected-min.rpt
set start {$auto$ff.cc:337:slice$292119/Q}
set end {$auto$ff.cc:337:slice$283401/D}
set sp [get_pins [list $start]];set ep [get_pins [list $end]]
if {[llength $sp]!=1 || [llength $ep]!=1} {error "Missing paired data path $start -> $end"}
set paths [find_timing_paths -from $sp -to $ep -path_delay min -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained paired path $start -> $end"}
puts $f "$start	$end	[get_property [lindex $paths 0] slack]"
report_checks -from $sp -to $ep -path_delay min -group_path_count 1 -endpoint_path_count 1 -digits 9 -format full_clock_expanded >> selected-min.rpt
set start {$auto$ff.cc:337:slice$315032/Q}
set end {$auto$ff.cc:337:slice$318644/D}
set sp [get_pins [list $start]];set ep [get_pins [list $end]]
if {[llength $sp]!=1 || [llength $ep]!=1} {error "Missing paired data path $start -> $end"}
set paths [find_timing_paths -from $sp -to $ep -path_delay min -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained paired path $start -> $end"}
puts $f "$start	$end	[get_property [lindex $paths 0] slack]"
report_checks -from $sp -to $ep -path_delay min -group_path_count 1 -endpoint_path_count 1 -digits 9 -format full_clock_expanded >> selected-min.rpt
set start {$auto$ff.cc:337:slice$318230/Q}
set end {$auto$ff.cc:337:slice$316702/D}
set sp [get_pins [list $start]];set ep [get_pins [list $end]]
if {[llength $sp]!=1 || [llength $ep]!=1} {error "Missing paired data path $start -> $end"}
set paths [find_timing_paths -from $sp -to $ep -path_delay min -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained paired path $start -> $end"}
puts $f "$start	$end	[get_property [lindex $paths 0] slack]"
report_checks -from $sp -to $ep -path_delay min -group_path_count 1 -endpoint_path_count 1 -digits 9 -format full_clock_expanded >> selected-min.rpt
set start {$auto$ff.cc:337:slice$318752/Q}
set end {$auto$ff.cc:337:slice$316700/D}
set sp [get_pins [list $start]];set ep [get_pins [list $end]]
if {[llength $sp]!=1 || [llength $ep]!=1} {error "Missing paired data path $start -> $end"}
set paths [find_timing_paths -from $sp -to $ep -path_delay min -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained paired path $start -> $end"}
puts $f "$start	$end	[get_property [lindex $paths 0] slack]"
report_checks -from $sp -to $ep -path_delay min -group_path_count 1 -endpoint_path_count 1 -digits 9 -format full_clock_expanded >> selected-min.rpt
set start {$auto$ff.cc:337:slice$343675/Q}
set end {$auto$ff.cc:337:slice$335633/D}
set sp [get_pins [list $start]];set ep [get_pins [list $end]]
if {[llength $sp]!=1 || [llength $ep]!=1} {error "Missing paired data path $start -> $end"}
set paths [find_timing_paths -from $sp -to $ep -path_delay min -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained paired path $start -> $end"}
puts $f "$start	$end	[get_property [lindex $paths 0] slack]"
report_checks -from $sp -to $ep -path_delay min -group_path_count 1 -endpoint_path_count 1 -digits 9 -format full_clock_expanded >> selected-min.rpt
set start {$auto$ff.cc:337:slice$358457/Q}
set end {$auto$ff.cc:337:slice$358787/D}
set sp [get_pins [list $start]];set ep [get_pins [list $end]]
if {[llength $sp]!=1 || [llength $ep]!=1} {error "Missing paired data path $start -> $end"}
set paths [find_timing_paths -from $sp -to $ep -path_delay min -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained paired path $start -> $end"}
puts $f "$start	$end	[get_property [lindex $paths 0] slack]"
report_checks -from $sp -to $ep -path_delay min -group_path_count 1 -endpoint_path_count 1 -digits 9 -format full_clock_expanded >> selected-min.rpt
set start {$auto$ff.cc:337:slice$367363/Q}
set end {$auto$ff.cc:337:slice$369111/D}
set sp [get_pins [list $start]];set ep [get_pins [list $end]]
if {[llength $sp]!=1 || [llength $ep]!=1} {error "Missing paired data path $start -> $end"}
set paths [find_timing_paths -from $sp -to $ep -path_delay min -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained paired path $start -> $end"}
puts $f "$start	$end	[get_property [lindex $paths 0] slack]"
report_checks -from $sp -to $ep -path_delay min -group_path_count 1 -endpoint_path_count 1 -digits 9 -format full_clock_expanded >> selected-min.rpt
set start {$auto$ff.cc:337:slice$379847/Q}
set end {$auto$ff.cc:337:slice$262216/D}
set sp [get_pins [list $start]];set ep [get_pins [list $end]]
if {[llength $sp]!=1 || [llength $ep]!=1} {error "Missing paired data path $start -> $end"}
set paths [find_timing_paths -from $sp -to $ep -path_delay min -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained paired path $start -> $end"}
puts $f "$start	$end	[get_property [lindex $paths 0] slack]"
report_checks -from $sp -to $ep -path_delay min -group_path_count 1 -endpoint_path_count 1 -digits 9 -format full_clock_expanded >> selected-min.rpt
set start {$auto$ff.cc:337:slice$394012/Q}
set end {$auto$ff.cc:337:slice$395898/D}
set sp [get_pins [list $start]];set ep [get_pins [list $end]]
if {[llength $sp]!=1 || [llength $ep]!=1} {error "Missing paired data path $start -> $end"}
set paths [find_timing_paths -from $sp -to $ep -path_delay min -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained paired path $start -> $end"}
puts $f "$start	$end	[get_property [lindex $paths 0] slack]"
report_checks -from $sp -to $ep -path_delay min -group_path_count 1 -endpoint_path_count 1 -digits 9 -format full_clock_expanded >> selected-min.rpt
set start {$auto$ff.cc:337:slice$397852/Q}
set end {$auto$ff.cc:337:slice$399672/D}
set sp [get_pins [list $start]];set ep [get_pins [list $end]]
if {[llength $sp]!=1 || [llength $ep]!=1} {error "Missing paired data path $start -> $end"}
set paths [find_timing_paths -from $sp -to $ep -path_delay min -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained paired path $start -> $end"}
puts $f "$start	$end	[get_property [lindex $paths 0] slack]"
report_checks -from $sp -to $ep -path_delay min -group_path_count 1 -endpoint_path_count 1 -digits 9 -format full_clock_expanded >> selected-min.rpt
set start {$auto$ff.cc:337:slice$398033/Q}
set end {$auto$ff.cc:337:slice$399688/D}
set sp [get_pins [list $start]];set ep [get_pins [list $end]]
if {[llength $sp]!=1 || [llength $ep]!=1} {error "Missing paired data path $start -> $end"}
set paths [find_timing_paths -from $sp -to $ep -path_delay min -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained paired path $start -> $end"}
puts $f "$start	$end	[get_property [lindex $paths 0] slack]"
report_checks -from $sp -to $ep -path_delay min -group_path_count 1 -endpoint_path_count 1 -digits 9 -format full_clock_expanded >> selected-min.rpt
set start {$auto$ff.cc:337:slice$398285/Q}
set end {$auto$ff.cc:337:slice$399679/D}
set sp [get_pins [list $start]];set ep [get_pins [list $end]]
if {[llength $sp]!=1 || [llength $ep]!=1} {error "Missing paired data path $start -> $end"}
set paths [find_timing_paths -from $sp -to $ep -path_delay min -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained paired path $start -> $end"}
puts $f "$start	$end	[get_property [lindex $paths 0] slack]"
report_checks -from $sp -to $ep -path_delay min -group_path_count 1 -endpoint_path_count 1 -digits 9 -format full_clock_expanded >> selected-min.rpt
set start {$auto$ff.cc:337:slice$398324/Q}
set end {$auto$ff.cc:337:slice$399686/D}
set sp [get_pins [list $start]];set ep [get_pins [list $end]]
if {[llength $sp]!=1 || [llength $ep]!=1} {error "Missing paired data path $start -> $end"}
set paths [find_timing_paths -from $sp -to $ep -path_delay min -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained paired path $start -> $end"}
puts $f "$start	$end	[get_property [lindex $paths 0] slack]"
report_checks -from $sp -to $ep -path_delay min -group_path_count 1 -endpoint_path_count 1 -digits 9 -format full_clock_expanded >> selected-min.rpt
set start {$auto$ff.cc:337:slice$425212/Q}
set end {$auto$ff.cc:337:slice$425344/D}
set sp [get_pins [list $start]];set ep [get_pins [list $end]]
if {[llength $sp]!=1 || [llength $ep]!=1} {error "Missing paired data path $start -> $end"}
set paths [find_timing_paths -from $sp -to $ep -path_delay min -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained paired path $start -> $end"}
puts $f "$start	$end	[get_property [lindex $paths 0] slack]"
report_checks -from $sp -to $ep -path_delay min -group_path_count 1 -endpoint_path_count 1 -digits 9 -format full_clock_expanded >> selected-min.rpt
set start {$auto$ff.cc:337:slice$439598/Q}
set end {$auto$ff.cc:337:slice$439763/D}
set sp [get_pins [list $start]];set ep [get_pins [list $end]]
if {[llength $sp]!=1 || [llength $ep]!=1} {error "Missing paired data path $start -> $end"}
set paths [find_timing_paths -from $sp -to $ep -path_delay min -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained paired path $start -> $end"}
puts $f "$start	$end	[get_property [lindex $paths 0] slack]"
report_checks -from $sp -to $ep -path_delay min -group_path_count 1 -endpoint_path_count 1 -digits 9 -format full_clock_expanded >> selected-min.rpt
set start {$auto$ff.cc:337:slice$441971/Q}
set end {$auto$ff.cc:337:slice$439945/D}
set sp [get_pins [list $start]];set ep [get_pins [list $end]]
if {[llength $sp]!=1 || [llength $ep]!=1} {error "Missing paired data path $start -> $end"}
set paths [find_timing_paths -from $sp -to $ep -path_delay min -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained paired path $start -> $end"}
puts $f "$start	$end	[get_property [lindex $paths 0] slack]"
report_checks -from $sp -to $ep -path_delay min -group_path_count 1 -endpoint_path_count 1 -digits 9 -format full_clock_expanded >> selected-min.rpt
set start {$auto$ff.cc:337:slice$447751/Q}
set end {$auto$ff.cc:337:slice$447946/D}
set sp [get_pins [list $start]];set ep [get_pins [list $end]]
if {[llength $sp]!=1 || [llength $ep]!=1} {error "Missing paired data path $start -> $end"}
set paths [find_timing_paths -from $sp -to $ep -path_delay min -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained paired path $start -> $end"}
puts $f "$start	$end	[get_property [lindex $paths 0] slack]"
report_checks -from $sp -to $ep -path_delay min -group_path_count 1 -endpoint_path_count 1 -digits 9 -format full_clock_expanded >> selected-min.rpt
set start {$auto$ff.cc:337:slice$459848/Q}
set end {$auto$ff.cc:337:slice$460936/D}
set sp [get_pins [list $start]];set ep [get_pins [list $end]]
if {[llength $sp]!=1 || [llength $ep]!=1} {error "Missing paired data path $start -> $end"}
set paths [find_timing_paths -from $sp -to $ep -path_delay min -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained paired path $start -> $end"}
puts $f "$start	$end	[get_property [lindex $paths 0] slack]"
report_checks -from $sp -to $ep -path_delay min -group_path_count 1 -endpoint_path_count 1 -digits 9 -format full_clock_expanded >> selected-min.rpt
set start {$auto$ff.cc:337:slice$464749/Q}
set end {$auto$ff.cc:337:slice$466603/D}
set sp [get_pins [list $start]];set ep [get_pins [list $end]]
if {[llength $sp]!=1 || [llength $ep]!=1} {error "Missing paired data path $start -> $end"}
set paths [find_timing_paths -from $sp -to $ep -path_delay min -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained paired path $start -> $end"}
puts $f "$start	$end	[get_property [lindex $paths 0] slack]"
report_checks -from $sp -to $ep -path_delay min -group_path_count 1 -endpoint_path_count 1 -digits 9 -format full_clock_expanded >> selected-min.rpt
set start {$auto$ff.cc:337:slice$464862/Q}
set end {$auto$ff.cc:337:slice$466620/D}
set sp [get_pins [list $start]];set ep [get_pins [list $end]]
if {[llength $sp]!=1 || [llength $ep]!=1} {error "Missing paired data path $start -> $end"}
set paths [find_timing_paths -from $sp -to $ep -path_delay min -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained paired path $start -> $end"}
puts $f "$start	$end	[get_property [lindex $paths 0] slack]"
report_checks -from $sp -to $ep -path_delay min -group_path_count 1 -endpoint_path_count 1 -digits 9 -format full_clock_expanded >> selected-min.rpt
close $f
