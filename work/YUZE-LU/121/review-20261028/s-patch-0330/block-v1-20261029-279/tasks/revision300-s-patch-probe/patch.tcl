set_thread_count 16
read_db {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/block-v1-20261028-246/tasks/revision300-route-s/flow/results/nangate45/bv1_block_v1_s16k/base/5_2_route.odb}
set block [ord::get_db_block]
set matches {}
foreach net [$block getNets] {
  if {[string map [list [format %c 92] {}] [$net getName]] eq {words[674][3]}} {
    lappend matches $net
  }
}
if {[llength $matches] != 1} {error "Ambiguous target net"}
set net [lindex $matches 0]
set wire [$net getWire]
set encoder [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $encoder $wire
odb::dbWireEncoder_newPath $encoder [[ord::get_db_tech] findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $encoder 362260 1806770
odb::dbWireEncoder_addRect $encoder 0 0 200 60
odb::dbWireEncoder_end $encoder
odb::delete_dbWireEncoder $encoder
write_db patched.odb
write_def patched.def
drt::check_drc_cmd patched-native-drc.rpt 0 0 0 0 native_whole_drc
puts SAME_NET_PATCH_PROBE_COMPLETE
