set_thread_count 16
read_liberty /OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib
read_db {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/block-v1-20261029-380/tasks/revision300-route-v/flow/results/nangate45/bv1_block_v1_v/base/6_final.odb}
set out [open pg-status.tsv w]
foreach net {VDD VSS} {
 puts "BEGIN_PG $net"
 set code [catch {check_power_grid -net $net -error_file $net.rpt} msg]
 puts $out "$net\t$code\t$msg"
 flush $out
 puts "END_PG $net $code $msg"
}
close $out
