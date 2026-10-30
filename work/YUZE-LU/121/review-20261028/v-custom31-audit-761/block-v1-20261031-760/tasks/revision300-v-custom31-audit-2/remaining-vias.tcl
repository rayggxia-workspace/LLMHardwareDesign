set_thread_count 16
read_db {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/block-v1-20261031-705/tasks/revision300-v-joint-via-compose/local-candidate.odb}
set block [ord::get_db_block]
set tech [ord::get_db_tech]
set wanted [dict create]
if {[$tech getManufacturingGrid] != 10} {error {Manufacturing grid mismatch}}
dict set wanted [encoding convertfrom utf-8 [binary decode hex {246162632431343134303338246e65775f6e333731353439}]] 1
set selected [dict create]
foreach net [$block getNets] {set name [string map [list [format %c 92] {}] [$net getName]];if {[dict exists $wanted $name]} {if {[dict exists $selected $name]} {error "Ambiguous target"};dict set selected $name $net}}
if {[dict size $selected] != 1} {error "Missing target"}
if {[$tech findVia BV1_M3_21_2_0] != "NULL"} {error {Custom via already exists}}
set custom [odb::dbTechVia_create $tech BV1_M3_21_2_0]
odb::dbBox_create $custom [$tech findLayer via3] -70 -70 70 70
odb::dbBox_create $custom [$tech findLayer metal3] -140 -70 260 70
odb::dbBox_create $custom [$tech findLayer metal4] -140 -140 140 140
set got {}
foreach box [$custom getBoxes] {lappend got [list [[$box getTechLayer] getName] [$box xMin] [$box yMin] [$box xMax] [$box yMax]]}
if {[lsort $got] ne [lsort {{via3 -70 -70 70 70} {metal3 -140 -70 260 70} {metal4 -140 -140 140 140}}]} {error {Custom via actual shape mismatch}}
if {[$tech findVia BV1_M3_21_2_1] != "NULL"} {error {Custom via already exists}}
set custom [odb::dbTechVia_create $tech BV1_M3_21_2_1]
odb::dbBox_create $custom [$tech findLayer via2] -70 -70 70 70
odb::dbBox_create $custom [$tech findLayer metal2] -70 -140 70 140
odb::dbBox_create $custom [$tech findLayer metal3] -260 -70 140 70
set got {}
foreach box [$custom getBoxes] {lappend got [list [[$box getTechLayer] getName] [$box xMin] [$box yMin] [$box xMax] [$box yMax]]}
if {[lsort $got] ne [lsort {{via2 -70 -70 70 70} {metal2 -70 -140 70 140} {metal3 -260 -70 140 70}}]} {error {Custom via actual shape mismatch}}
set net [dict get $selected [encoding convertfrom utf-8 [binary decode hex {246162632431343134303338246e65775f6e333731353439}]]]
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_begin $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 160910 1837500
odb::dbWireEncoder_addPoint $enc 161310 1837500
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 160550 1789620
odb::dbWireEncoder_addPoint $enc 160910 1789620
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 160550 1779260
odb::dbWireEncoder_addPoint $enc 160550 1789620
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 160910 1789620
odb::dbWireEncoder_addPoint $enc 160910 1837500
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 160910 1837500
odb::dbWireEncoder_addTechVia $enc [$tech findVia BV1_M3_21_2_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 161310 1837500
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_7]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 161310 1837500
odb::dbWireEncoder_addTechVia $enc [$tech findVia BV1_M3_21_2_1]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 160910 1789620
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 160550 1789620
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 160550 1779260
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
write_db local-candidate.odb
write_def local-candidate.def
drt::check_drc_cmd local-native-drc.rpt 0 0 0 0 native_whole_drc
