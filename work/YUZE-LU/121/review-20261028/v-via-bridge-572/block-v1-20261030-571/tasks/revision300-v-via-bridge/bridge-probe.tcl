set_thread_count 16
read_db {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/block-v1-20261030-523/tasks/revision300-final-source-v/flow/results/nangate45/bv1_block_v1_v/base/6_final.odb}
set block [ord::get_db_block]
set tech [ord::get_db_tech]
set matches {}
set wanted [encoding convertfrom utf-8 [binary decode hex {24666c617474656e66756e6374696f6e5f756e69742e246162632431383031393034246e65775f6e3138323139}]]
foreach net [$block getNets] {if {[string map [list [format %c 92] {}] [$net getName]] eq $wanted} {lappend matches $net}}
if {[llength $matches] != 1} {error "Ambiguous target"}
set net [lindex $matches 0]
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_begin $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2325410 1598100
odb::dbWireEncoder_addPoint $enc 2325410 1598940
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2325030 1598940
odb::dbWireEncoder_addPoint $enc 2325410 1598940
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2325030 1598940
odb::dbWireEncoder_addPoint $enc 2325030 1600060
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2325790 1575700
odb::dbWireEncoder_addPoint $enc 2325790 1598100
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 2325410 1598100
odb::dbWireEncoder_addPoint $enc 2325790 1598100
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 2325030 1600060
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 2325790 1575700
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_7]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 2325790 1598100
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_7]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2325410 1598100
odb::dbWireEncoder_addPoint $enc 2325790 1598100
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
write_db bridge-candidate.odb
write_def bridge-candidate.def
drt::check_drc_cmd bridge-native-drc.rpt 0 0 0 0 native_whole_drc
