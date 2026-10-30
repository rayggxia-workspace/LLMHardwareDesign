set_thread_count 16
read_db {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/block-v1-20261030-598/tasks/revision300-v-geometry-compose/composed-candidate.odb}
set block [ord::get_db_block]
set tech [ord::get_db_tech]
set v [$tech findVia via1_7];set seen {}
foreach part [$v getBoxes] {set layer [[$part getTechLayer] getName];if {[string match metal* $layer]} {lappend seen $layer}}
if {[lsort -unique $seen] ne [lsort [list metal1 metal2]]} {error "Actual via metal layers mismatch"}
set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343337323234246e65775f6e313035323635}]]
set selected {}
foreach net [$block getNets] {if {[string map [list [format %c 92] {}] [$net getName]] eq $wanted} {lappend selected $net}}
if {[llength $selected]!=1} {error "Ambiguous target"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_begin $enc [[lindex $selected 0] getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 361190 1337700
odb::dbWireEncoder_addPoint $enc 361190 1337980
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 360810 1337980
odb::dbWireEncoder_addPoint $enc 361190 1337980
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 360810 1337980
odb::dbWireEncoder_addPoint $enc 360810 1339940
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 360810 1339940
odb::dbWireEncoder_addPoint $enc 361190 1339940
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 361190 1339940
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 361190 1337700
odb::dbWireEncoder_addPoint $enc 361190 1337980
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 361190 1337980
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_7]
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
write_db transition-candidate.odb
write_def transition-candidate.def
drt::check_drc_cmd transition-native-drc.rpt 0 0 0 0 native_whole_drc
