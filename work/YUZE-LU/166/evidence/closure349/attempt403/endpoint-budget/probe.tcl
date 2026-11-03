set_thread_count 16
read_liberty /OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib
read_db {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-166-r-local-state/attempt349/physical/flow/results/nangate45/r166_1024/base/6_final.odb}
read_sdc {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-166-r-local-state/attempt349/physical/flow/results/nangate45/r166_1024/base/6_final.sdc}
read_spef {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-166-r-local-state/attempt349/physical/flow/results/nangate45/r166_1024/base/6_final.spef}
set_propagated_clock [all_clocks]
sta::find_timing
set f [open endpoint-budgets.tsv w]
set name {$auto$ff.cc:337:slice$230525/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	-0.000358	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$232107/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	-0.011628	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$232108/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	-0.006719	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$232109/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	-0.006689	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$232118/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	-0.007337	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$239085/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	-0.022584	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$241178/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	-0.022398	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$241601/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	-0.036165	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$248278/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	-0.022275	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$252130/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	-0.008055	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$255167/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	-0.005025	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$255172/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	-0.004107	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$255196/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	-0.006657	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$258683/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	-0.006556	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$285565/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	-0.022784	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$285571/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	-0.021743	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$292454/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	-0.005267	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$316708/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	-0.005922	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$327647/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	-0.003864	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$345975/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	-0.025528	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$345982/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	-0.02371	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$348522/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	-0.002469	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$367240/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	-0.007746	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$367372/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	-0.005836	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$375485/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	-0.006132	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$377452/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	-0.001288	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$395922/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	-0.004794	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$398395/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	-0.009711	[get_property [lindex $paths 0] slack]"
close $f
