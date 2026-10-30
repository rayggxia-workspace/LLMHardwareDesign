set_thread_count 16
read_db {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/block-v1-20261030-400/tasks/revision300-route-v/flow/results/nangate45/bv1_block_v1_v/base/5_2_route.odb}
write_def before.def
write_verilog before.v
set net [[ord::get_db_block] findNet {$abc$1405522$new_n120169}]
if {$net eq "NULL"} {error "Missing probe net"}
set encoder [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $encoder [$net getWire]
odb::dbWireEncoder_newPath $encoder [[ord::get_db_tech] findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $encoder 2196590 790860
odb::dbWireEncoder_addPoint $encoder 2196590 791140
odb::dbWireEncoder_end $encoder
odb::delete_dbWireEncoder $encoder
write_def after.def
write_verilog after.v
write_db probe.odb
drt::check_drc_cmd native-whole-drc.rpt 0 0 0 0 native_whole_drc
