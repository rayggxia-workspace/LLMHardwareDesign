set_thread_count 16
read_liberty /OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib
read_db {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/block-v1-20261029-380/tasks/revision300-route-v/flow/results/nangate45/bv1_block_v1_v/base/6_final.odb}
puts "BEGIN_PRE_RCX_PG"
set code [catch {check_power_grid -net VSS -error_file pre-rcx-vss.rpt} msg]
set out [open pg-status.tsv w]
puts $out "$code\t$msg"
close $out
puts "END_PRE_RCX_PG $code $msg"
