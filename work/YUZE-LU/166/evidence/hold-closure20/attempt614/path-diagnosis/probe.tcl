set_thread_count 16
read_liberty /OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib
read_db {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-166-r-local-state/attempt596/physical/flow/results/nangate45/r166_1024/base/6_final.odb}
read_sdc {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-166-r-local-state/attempt596/physical/flow/results/nangate45/r166_1024/base/6_final.sdc}
read_spef {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-166-r-local-state/attempt596/physical/flow/results/nangate45/r166_1024/base/6_final.spef}
set_propagated_clock [all_clocks]
sta::find_timing
set f [open failing-paths.tsv w]
foreach kind {min max} {
 set cutoff [expr {$kind eq "min" ? 0.01 : 0}]
 foreach path [find_timing_paths -path_delay $kind -slack_max $cutoff -group_path_count 200000 -endpoint_path_count 1] {
  puts $f "$kind	[get_full_name [get_property $path startpoint]]	[get_full_name [get_property $path endpoint]]	[get_property $path slack]"
 }
}
close $f
report_checks -path_delay min_max -group_path_count 20 -digits 9 -format full_clock_expanded > paths.rpt
