set_thread_count 16
read_liberty /OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib
read_db {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-166-r-local-state/attempt628/physical/CLOCK_POST_RESTORE.odb}
foreach net {VDD VSS} {set code [catch {check_power_grid -net $net -error_file ${net}.rpt} message];puts "R166_DIAG_BOTH_PG; net=$net; code=$code; message=$message"}
