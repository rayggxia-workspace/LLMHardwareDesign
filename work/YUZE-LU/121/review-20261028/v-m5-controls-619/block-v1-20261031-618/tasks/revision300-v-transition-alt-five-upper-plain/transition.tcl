set_thread_count 16
read_db {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/block-v1-20261030-598/tasks/revision300-v-geometry-compose/composed-candidate.odb}
set block [ord::get_db_block]
set tech [ord::get_db_tech]
set v [$tech findVia via3_2];set seen {}
foreach part [$v getBoxes] {set layer [[$part getTechLayer] getName];if {[string match metal* $layer]} {lappend seen $layer}}
if {[lsort -unique $seen] ne [lsort [list metal3 metal4]]} {error "Actual via metal layers mismatch"}
set v [$tech findVia via2_5];set seen {}
foreach part [$v getBoxes] {set layer [[$part getTechLayer] getName];if {[string match metal* $layer]} {lappend seen $layer}}
if {[lsort -unique $seen] ne [lsort [list metal2 metal3]]} {error "Actual via metal layers mismatch"}
set v [$tech findVia via4_0];set seen {}
foreach part [$v getBoxes] {set layer [[$part getTechLayer] getName];if {[string match metal* $layer]} {lappend seen $layer}}
if {[lsort -unique $seen] ne [lsort [list metal4 metal5]]} {error "Actual via metal layers mismatch"}
set wanted [encoding convertfrom utf-8 [binary decode hex {6e65743830323338}]]
set selected {}
foreach net [$block getNets] {if {[string map [list [format %c 92] {}] [$net getName]] eq $wanted} {lappend selected $net}}
if {[llength $selected]!=1} {error "Ambiguous target"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_begin $enc [[lindex $selected 0] getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 87970 2067940
odb::dbWireEncoder_addPoint $enc 87970 2068500
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 60990 2151940
odb::dbWireEncoder_addPoint $enc 60990 2152500
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 60670 2152500
odb::dbWireEncoder_addPoint $enc 60990 2152500
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 60990 2149980
odb::dbWireEncoder_addPoint $enc 60990 2151940
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 70490 2112460
odb::dbWireEncoder_addPoint $enc 70490 2112740
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 79710 2112460
odb::dbWireEncoder_addPoint $enc 79710 2149980
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 58710 2168180
odb::dbWireEncoder_addPoint $enc 60670 2168180
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 58710 2168180
odb::dbWireEncoder_addPoint $enc 58710 2171260
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 60670 2152500
odb::dbWireEncoder_addPoint $enc 60670 2168180
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 113430 2056740
odb::dbWireEncoder_addPoint $enc 113430 2057300
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 112190 2057300
odb::dbWireEncoder_addPoint $enc 113430 2057300
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 113430 2057300
odb::dbWireEncoder_addPoint $enc 113870 2057300
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 87970 2068500
odb::dbWireEncoder_addPoint $enc 112190 2068500
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 97070 2144100
odb::dbWireEncoder_addPoint $enc 97070 2149980
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 97070 2144100
odb::dbWireEncoder_addPoint $enc 100510 2144100
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 100510 2143260
odb::dbWireEncoder_addPoint $enc 100510 2144100
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 60990 2149980
odb::dbWireEncoder_addPoint $enc 97070 2149980
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 113870 2027900
odb::dbWireEncoder_addPoint $enc 114430 2027900
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 114430 2026780
odb::dbWireEncoder_addPoint $enc 114430 2027900
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 113870 2026780
odb::dbWireEncoder_addPoint $enc 114430 2026780
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 113870 2023420
odb::dbWireEncoder_addPoint $enc 113870 2026780
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 108490 2023420
odb::dbWireEncoder_addPoint $enc 113870 2023420
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 108490 2017540
odb::dbWireEncoder_addPoint $enc 108490 2023420
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 113870 2027900
odb::dbWireEncoder_addPoint $enc 113870 2057300
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 99370 2088380
odb::dbWireEncoder_addPoint $enc 113810 2088380
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 99370 2088380
odb::dbWireEncoder_addPoint $enc 99370 2088660
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 83070 2088660
odb::dbWireEncoder_addPoint $enc 99370 2088660
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 83070 2088660
odb::dbWireEncoder_addPoint $enc 83070 2112460
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 70490 2112460
odb::dbWireEncoder_addPoint $enc 83070 2112460
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 112190 2057300
odb::dbWireEncoder_addPoint $enc 112190 2088380
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 87970 2067940
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 87970 2068500
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 60990 2151940
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 60990 2152500
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 60990 2149980
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 79710 2149980
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 70490 2112460
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 70490 2112740
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 79710 2112460
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 60670 2168180
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 58710 2168180
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 58710 2171260
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 113430 2056740
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 113430 2057300
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 112190 2057300
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 113870 2057300
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 112190 2068500
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 97070 2149980
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 97070 2144100
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 100510 2144100
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 100510 2143260
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 113870 2023420
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 108490 2023420
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 108490 2017540
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_4]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal1] ROUTED
odb::dbWireEncoder_addPoint $enc 113810 2088380
odb::dbWireEncoder_addTechVia $enc [$tech findVia via1_7]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 113810 2088380
odb::dbWireEncoder_addTechVia $enc [$tech findVia via2_5]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 83070 2088660
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 83070 2112460
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 112190 2088380
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal5] ROUTED
odb::dbWireEncoder_addPoint $enc 60670 2152500
odb::dbWireEncoder_addPoint $enc 60990 2152500
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 60990 2152500
odb::dbWireEncoder_addTechVia $enc [$tech findVia via3_2]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 60990 2152500
odb::dbWireEncoder_addTechVia $enc [$tech findVia via4_0]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal4] ROUTED
odb::dbWireEncoder_addPoint $enc 60670 2152500
odb::dbWireEncoder_addTechVia $enc [$tech findVia via4_0]
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
write_db transition-candidate.odb
write_def transition-candidate.def
drt::check_drc_cmd transition-native-drc.rpt 0 0 0 0 native_whole_drc
