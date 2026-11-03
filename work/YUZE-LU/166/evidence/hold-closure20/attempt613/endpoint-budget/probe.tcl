set_thread_count 16
read_liberty /OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib
read_db {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-166-r-local-state/attempt596/physical/flow/results/nangate45/r166_1024/base/6_final.odb}
read_sdc {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-166-r-local-state/attempt596/physical/flow/results/nangate45/r166_1024/base/6_final.sdc}
read_spef {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-166-r-local-state/attempt596/physical/flow/results/nangate45/r166_1024/base/6_final.spef}
set_propagated_clock [all_clocks]
sta::find_timing
set f [open endpoint-budgets.tsv w]
set name {$auto$ff.cc:337:slice$240800/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	0.001833	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$240843/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	0.001257	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$240988/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	0.004251	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$241629/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	0.001421	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$252180/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	0.001301	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$256811/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	0.001458	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$256812/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	0.002536	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$256819/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	-0.001079	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$262222/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	0.003549	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$264150/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	-0.008541	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$264153/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	-0.005116	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$272076/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	0.000192	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$283386/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	0.003903	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$283390/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	-0.008029	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$292189/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	0.00201	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$304412/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	0.00103	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$335646/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	0.002256	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$337258/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	0.004645	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$337269/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	0.000477	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$337273/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	0.001201	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$348668/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	0.000324	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$350481/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	0.000239	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$354135/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	0.003382	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$354346/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	0.004678	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$365530/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	0.003783	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$369109/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	-0.004844	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$369123/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	0.003686	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$369125/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	-0.0054	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$369127/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	-0.002449	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$370948/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	0.001572	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$371665/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	0.004109	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$375463/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	0.002191	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$377471/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	0.004012	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$381899/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	0.002481	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$386206/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	0.001504	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$391409/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	0.004012	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$399669/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	-0.005783	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$399676/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	0.002084	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$400325/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	0.002277	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$400337/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	0.004377	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$409480/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	0.002443	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$413658/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	0.002823	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$425327/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	0.000719	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$425333/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	0.004007	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$425339/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	0.001485	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$425340/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	0.001637	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$425341/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	-5e-06	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$429006/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	-0.003669	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$433551/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	0.004773	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$433914/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	0.00338	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$433930/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	0.004491	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$439093/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	0.001733	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$439096/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	0.000902	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$439102/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	0.00126	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$439105/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	0.004517	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$439119/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	0.001327	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$443890/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	0.003563	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$445980/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	0.003342	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$447265/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	0.002812	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$451647/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	0.002911	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$468502/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	0.003931	[get_property [lindex $paths 0] slack]"
set name {$auto$ff.cc:337:slice$468520/D}
set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name	0.003615	[get_property [lindex $paths 0] slack]"
close $f
