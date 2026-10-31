set_thread_count 16
read_db {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/block-v1-20261030-598/tasks/revision300-v-geometry-compose/composed-candidate.odb}
set block [ord::get_db_block]
set tech [ord::get_db_tech]
set v [$tech findVia via2_5];set seen {}
foreach part [$v getBoxes] {set layer [[$part getTechLayer] getName];if {[string match metal* $layer]} {lappend seen $layer}}
if {[lsort -unique $seen] ne [lsort [list metal2 metal3]]} {error "Actual via metal layers mismatch"}
set v [$tech findVia via2_5];set seen {}
foreach part [$v getBoxes] {set layer [[$part getTechLayer] getName];if {[string match metal* $layer]} {lappend seen $layer}}
if {[lsort -unique $seen] ne [lsort [list metal2 metal3]]} {error "Actual via metal layers mismatch"}
set v [$tech findVia via1_4];set seen {}
foreach part [$v getBoxes] {set layer [[$part getTechLayer] getName];if {[string match metal* $layer]} {lappend seen $layer}}
if {[lsort -unique $seen] ne [lsort [list metal1 metal2]]} {error "Actual via metal layers mismatch"}
set wanted [encoding convertfrom utf-8 [binary decode hex {696e7075745f6d656d5b3233375d5b32355d}]]
set selected {}
foreach net [$block getNets] {if {[string map [list [format %c 92] {}] [$net getName]] eq $wanted} {lappend selected $net}}
if {[llength $selected]!=1} {error "Ambiguous target"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_begin $enc [[lindex $selected 0] getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 79610 309540
odb::dbWireEncoder_addPoint $enc 83030 309540
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 79610 306460
odb::dbWireEncoder_addPoint $enc 79610 309540
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 87590 306460
odb::dbWireEncoder_addPoint $enc 87590 308700
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 83030 308700
odb::dbWireEncoder_addPoint $enc 87590 308700
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 83030 308700
odb::dbWireEncoder_addPoint $enc 83030 309540
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 86450 314580
odb::dbWireEncoder_addPoint $enc 86450 315140
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 86450 314580
odb::dbWireEncoder_addPoint $enc 87590 314580
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 87590 308700
odb::dbWireEncoder_addPoint $enc 87590 314580
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 84550 317100
odb::dbWireEncoder_addPoint $enc 86450 317100
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 86450 315140
odb::dbWireEncoder_addPoint $enc 86450 317100
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 84930 317100
odb::dbWireEncoder_addPoint $enc 84930 317660
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 83030 309540
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 83030 309540
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 79610 309540
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 79610 306460
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 87590 306460
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 87590 308700
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 83030 308700
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 86450 315140
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 86450 314580
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 87590 314580
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 84550 317100
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 86450 317100
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 84930 317660
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 84930 317100
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 84550 317100
odb::dbWireEncoder_addPoint $enc 84930 317100
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
write_db transition-candidate.odb
write_def transition-candidate.def
drt::check_drc_cmd transition-native-drc.rpt 0 0 0 0 native_whole_drc
