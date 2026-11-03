set_thread_count 16
read_liberty /OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib
read_db {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-166-r-local-state/attempt347/physical/flow/results/nangate45/r166_1024/base/6_final.odb}
read_sdc {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-166-r-local-state/attempt347/physical/flow/results/nangate45/r166_1024/base/6_final.sdc}
read_spef {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-166-r-local-state/attempt347/physical/flow/results/nangate45/r166_1024/base/6_final.spef}
set_propagated_clock [all_clocks]
sta::find_timing
set f [open endpoint-budgets.tsv w]
set name {$auto$ff.cc:337:slice$238352/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	-0.007603	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$242149/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	-0.019512	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$259414/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	-0.008101	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$264825/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	-2.2e-05	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$264832/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	-0.00857	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$284013/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	-0.000143	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$284015/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	-0.01299	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$284028/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	-0.006496	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$284036/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	-0.020722	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$286223/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	-0.033349	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$323102/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	-0.00922	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$331159/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	-0.001613	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$331168/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	-0.012777	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$331179/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	-0.008036	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$343691/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	-0.002066	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$359041/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	-0.000906	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$359044/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	-0.010765	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$359049/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	-0.008348	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$361609/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	-0.008909	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$361624/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	-0.001634	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$361628/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	-0.000722	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$361636/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	-0.003006	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$373756/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	-0.007428	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$384043/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	-0.002131	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$384052/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	-0.001259	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$389026/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	-0.008379	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$389041/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	-0.01966	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$396803/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	-0.000192	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$396833/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	-0.00324	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$410497/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	-0.014215	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$410500/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	-0.010706	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$410508/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	-0.01543	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$412939/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	-0.00623	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$412941/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	-0.000333	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$412963/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	-0.005699	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$414684/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	-0.006387	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$414690/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	-0.001189	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$422677/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	-0.00881	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$422679/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	-0.002245	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$422707/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	-0.001466	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$428155/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	-0.002191	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$428167/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	-0.000105	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$436353/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	-0.007565	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$436791/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	-0.000866	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$436811/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	-0.003204	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$441939/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	-0.005708	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$441942/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	-0.006354	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$441949/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	-0.004697	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$442773/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	-0.004394	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$442781/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	-0.010916	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$442783/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	-0.001731	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$450106/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	-0.011955	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$454460/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	-0.004572	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$454466/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	-0.007879	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$460373/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	-0.003924	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$465362/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	-0.000369	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$465448/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	-0.012891	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$465450/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	-0.000398	[get_property [lindex $paths 0] slack]"
close $f
