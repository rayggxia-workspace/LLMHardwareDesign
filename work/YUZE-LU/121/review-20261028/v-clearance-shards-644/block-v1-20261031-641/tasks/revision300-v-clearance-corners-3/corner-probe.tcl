set_thread_count 16
read_db {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/block-v1-20261030-589/tasks/revision300-final-source-v/flow/results/nangate45/bv1_block_v1_v/base/6_final.odb}
set block [ord::get_db_block]
set tech [ord::get_db_tech]
set exact [dict create]
foreach net [$block getNets] {set plain [string map [list [format %c 92] {}] [$net getName]];dict lappend exact $plain $net}
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {246162632431343134303338246175746f2472746c696c2e63633a333531333a4d7578476174652431333333313430}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1557360 729400
odb::dbWireEncoder_addRect $enc 0 0 900 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {246162632431343134303338246e65775f6e313338333030}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2076440 690200
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {246162632431343134303338246e65775f6e313433303937}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2315840 671720
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {246162632431343134303338246e65775f6e313433343730}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2354600 659960
odb::dbWireEncoder_addRect $enc 0 0 1660 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {246162632431343134303338246e65775f6e313932313839}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1514040 1680490
odb::dbWireEncoder_addRect $enc 0 0 900 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {246162632431343134303338246e65775f6e333031303634}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2072640 969070
odb::dbWireEncoder_addRect $enc 0 0 900 10
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {246162632431343134303338246e65775f6e333235393934}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 320460 1536920
odb::dbWireEncoder_addRect $enc 0 0 900 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {246162632431343134303338246e65775f6e333339333032}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1753440 1619520
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {246162632431343134303338246e65775f6e333432343831}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1041150 719950
odb::dbWireEncoder_addRect $enc 0 0 10 420
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {246162632431343134303338246e65775f6e343131343938}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 480440 1957480
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {696e7075745f6d656d5b3130355d5b31315d}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2315670 320950
odb::dbWireEncoder_addRect $enc 0 0 50 420
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {696e7075745f6d656d5b3234355d5b315d}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1238540 74410
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {696e7075745f6d656d5b35375d5b33305d}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 237240 500010
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e6574313032363735}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2391840 791000
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e6574313130353135}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1517840 2448600
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e6574313832343938}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 280940 591010
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e65743734313338}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1873140 1487920
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e65743734373236}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 237240 1493520
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e65743736373437}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 995340 2349760
odb::dbWireEncoder_addRect $enc 0 0 900 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e65743736383439}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 197340 1437170
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e65743835333137}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1797140 2017400
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e65743839323630}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1394340 2353050
odb::dbWireEncoder_addRect $enc 0 0 900 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e65743839363931}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2386730 955430
odb::dbWireEncoder_addRect $enc 0 0 110 420
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e65743930363735}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 277140 2101610
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e65743938323337}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2355740 1196370
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6f706572616e645f625b355d5b345d}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 795840 359450
odb::dbWireEncoder_addRect $enc 0 0 900 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6f75747075745f6d656d5b34325d5b32335d}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 277140 1704010
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {706f696e745f746f74616c5b375d5b36365d}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1474140 1062320
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {70726f647563745b335d5b31375d}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2112540 924770
odb::dbWireEncoder_addRect $enc 0 0 900 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
write_db corner-candidate.odb
write_def corner-candidate.def
drt::check_drc_cmd corner-native-drc.rpt 0 0 0 0 native_whole_drc
