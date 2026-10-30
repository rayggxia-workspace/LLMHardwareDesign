set_thread_count 16
read_db {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/block-v1-20261031-630/tasks/revision300-final-source-v/flow/results/nangate45/bv1_block_v1_v/base/6_final.odb}
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
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {246162632431343134303338246175746f2472746c696c2e63633a333531333a4d7578476174652431333339333538}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 121340 960890
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {246162632431343134303338246175746f2472746c696c2e63633a333531333a4d7578476174652431333830373930}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 360740 573650
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {246162632431343134303338246e65775f6e313034323839}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1038660 814170
odb::dbWireEncoder_addRect $enc 0 0 900 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {246162632431343134303338246e65775f6e313035313436}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1118460 1101520
odb::dbWireEncoder_addRect $enc 0 0 900 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {246162632431343134303338246e65775f6e313035333933}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1115040 1160600
odb::dbWireEncoder_addRect $enc 0 0 900 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {246162632431343134303338246e65775f6e313036303535}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1078940 1163120
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {246162632431343134303338246e65775f6e313138343531}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 639660 323960
odb::dbWireEncoder_addRect $enc 0 0 900 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {246162632431343134303338246e65775f6e313235313337}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 640040 603330
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {246162632431343134303338246e65775f6e313235343832}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 622770 636230
odb::dbWireEncoder_addRect $enc 0 0 70 700
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {246162632431343134303338246e65775f6e313239323530}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2475060 777560
odb::dbWireEncoder_addRect $enc 0 0 900 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {246162632431343134303338246e65775f6e313335393634}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2032740 572250
odb::dbWireEncoder_addRect $enc 0 0 900 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {246162632431343134303338246e65775f6e313338313332}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2115960 754250
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
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {246162632431343134303338246e65775f6e313339343039}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1996260 720930
odb::dbWireEncoder_addRect $enc 0 0 900 70
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
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {246162632431343134303338246e65775f6e313433323535}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2351940 662410
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
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {246162632431343134303338246e65775f6e313433373030}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2391840 656600
odb::dbWireEncoder_addRect $enc 0 0 1280 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {246162632431343134303338246e65775f6e313435343036}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2156240 488600
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {246162632431343134303338246e65775f6e313435373130}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2355360 487970
odb::dbWireEncoder_addRect $enc 0 0 900 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {246162632431343134303338246e65775f6e313438383832}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2036540 516600
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {246162632431343134303338246e65775f6e313439343032}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1557740 304640
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {246162632431343134303338246e65775f6e313533323234}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1314540 401520
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {246162632431343134303338246e65775f6e313535343330}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1553940 437570
odb::dbWireEncoder_addRect $enc 0 0 1280 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {246162632431343134303338246e65775f6e313632313932}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2431740 315000
odb::dbWireEncoder_addRect $enc 0 0 1280 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {246162632431343134303338246e65775f6e313637323537}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 636240 74410
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {246162632431343134303338246e65775f6e313730393630}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1793340 295050
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {246162632431343134303338246e65775f6e313732303534}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1593840 171070
odb::dbWireEncoder_addRect $enc 0 0 520 10
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {246162632431343134303338246e65775f6e313737303634}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1793340 164360
odb::dbWireEncoder_addRect $enc 0 0 900 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {246162632431343134303338246e65775f6e313738343335}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 799260 118650
odb::dbWireEncoder_addRect $enc 0 0 900 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {246162632431343134303338246e65775f6e313739383638}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2032740 243880
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {246162632431343134303338246e65775f6e313831383732}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 436740 275240
odb::dbWireEncoder_addRect $enc 0 0 200 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {246162632431343134303338246e65775f6e313930333030}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1876940 98210
odb::dbWireEncoder_addRect $enc 0 0 520 70
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
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {246162632431343134303338246e65775f6e323034343434}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 77640 1869210
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {246162632431343134303338246e65775f6e323035343330}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2192340 1706040
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {246162632431343134303338246e65775f6e323039303731}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 77640 2252320
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {246162632431343134303338246e65775f6e323131323138}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 795840 1193640
odb::dbWireEncoder_addRect $enc 0 0 900 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {246162632431343134303338246e65775f6e323136313939}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1314540 2065560
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {246162632431343134303338246e65775f6e323231313338}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1078560 1518370
odb::dbWireEncoder_addRect $enc 0 0 900 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {246162632431343134303338246e65775f6e323332333931}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2192340 2211440
odb::dbWireEncoder_addRect $enc 0 0 1280 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {246162632431343134303338246e65775f6e323336383430}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1793340 2471210
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {246162632431343134303338246e65775f6e323432303339}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1234740 1721090
odb::dbWireEncoder_addRect $enc 0 0 200 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {246162632431343134303338246e65775f6e323439303237}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2315460 2347450
odb::dbWireEncoder_addRect $enc 0 0 900 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {246162632431343134303338246e65775f6e323530343530}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1677440 1600130
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {246162632431343134303338246e65775f6e323539393938}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 161240 2405690
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {246162632431343134303338246e65775f6e323637373933}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 77640 721280
odb::dbWireEncoder_addRect $enc 0 0 1280 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {246162632431343134303338246e65775f6e323731323533}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 200760 743960
odb::dbWireEncoder_addRect $enc 0 0 900 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {246162632431343134303338246e65775f6e323733353835}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 280560 863240
odb::dbWireEncoder_addRect $enc 0 0 900 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {246162632431343134303338246e65775f6e323738303230}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 995340 569520
odb::dbWireEncoder_addRect $enc 0 0 900 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {246162632431343134303338246e65775f6e323831393837}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 596340 1049720
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {246162632431343134303338246e65775f6e323930313334}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2116340 171080
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {246162632431343134303338246e65775f6e323930373937}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1474140 132440
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {246162632431343134303338246e65775f6e323931303335}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 81440 417480
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {246162632431343134303338246e65775f6e323931323538}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 436740 455770
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {246162632431343134303338246e65775f6e323931363834}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 439780 193410
odb::dbWireEncoder_addRect $enc 0 0 1280 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {246162632431343134303338246e65775f6e323933313033}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 80680 193410
odb::dbWireEncoder_addRect $enc 0 0 1280 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {246162632431343134303338246e65775f6e323934313138}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 995340 134050
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {246162632431343134303338246e65775f6e323937353737}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1636780 67410
odb::dbWireEncoder_addRect $enc 0 0 1280 70
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
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {246162632431343134303338246e65775f6e333033383634}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1873140 866320
odb::dbWireEncoder_addRect $enc 0 0 900 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {246162632431343134303338246e65775f6e333139313935}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1234740 1563800
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {246162632431343134303338246e65775f6e333233343339}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 161240 1361640
odb::dbWireEncoder_addRect $enc 0 0 520 70
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
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {246162632431343134303338246e65775f6e333330393438}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 240660 2048410
odb::dbWireEncoder_addRect $enc 0 0 900 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {246162632431343134303338246e65775f6e333331363337}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 995340 2090760
odb::dbWireEncoder_addRect $enc 0 0 900 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {246162632431343134303338246e65775f6e333334333037}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 875640 2367610
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {246162632431343134303338246e65775f6e333338333832}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1038660 1914570
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
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {246162632431343134303338246e65775f6e333434353635}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 959240 1357720
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {246162632431343134303338246e65775f6e333530333536}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 277140 2317490
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {246162632431343134303338246e65775f6e333533343136}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 320840 2079770
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {246162632431343134303338246e65775f6e333630393835}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2275940 1537970
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {246162632431343134303338246e65775f6e333632393036}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1833240 1889370
odb::dbWireEncoder_addRect $enc 0 0 900 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {246162632431343134303338246e65775f6e333635333631}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1118840 758520
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {246162632431343134303338246e65775f6e333635373134}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1597640 1295000
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {246162632431343134303338246e65775f6e333637343038}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1078940 1275960
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {246162632431343134303338246e65775f6e333730343430}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 480440 1751330
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {246162632431343134303338246e65775f6e333731333235}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 157440 1590050
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {246162632431343134303338246e65775f6e333736303438}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 440540 2119810
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {246162632431343134303338246e65775f6e333936363034}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2115960 1887760
odb::dbWireEncoder_addRect $enc 0 0 900 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {246162632431343134303338246e65775f6e343030363134}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1557740 2331210
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {246162632431343134303338246e65775f6e343131333939}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1633740 2141720
odb::dbWireEncoder_addRect $enc 0 0 520 70
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
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {246162632431343134303338246e65775f6e343134363533}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1557740 925400
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {246162632431343134303338246e65775f6e343139313239}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 998380 1255450
odb::dbWireEncoder_addRect $enc 0 0 1280 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {246162632431343134303338246e65775f6e3536323833}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2272140 2166080
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {246162632431343134303338246e65775f6e3536353235}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2112540 1953840
odb::dbWireEncoder_addRect $enc 0 0 900 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {246162632431343134303338246e65775f6e3635373138}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2076440 911330
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {246162632431343134303338246e65775f6e3639373735}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1514040 1261400
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {246162632431343134303338246e65775f6e3832303333}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1234740 510720
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {246162632431343134303338246e65775f6e3836373533}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2076440 1222410
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {246162632431343134303338246e65775f6e3837343738}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2036160 1242080
odb::dbWireEncoder_addRect $enc 0 0 900 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {246162632431343134303338246e65775f6e3837393939}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1873140 831250
odb::dbWireEncoder_addRect $enc 0 0 200 70
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1873140 831250
odb::dbWireEncoder_addRect $enc 0 0 200 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {246162632431343134303338246e65775f6e3931373630}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1757620 636160
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {246162632431343134303338246e65775f6e3934343233}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1677440 599970
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {246162632431343134303338246e65775f6e3938323034}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 719840 1073730
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {24666c617474656e66756e6374696f6e5f756e69742e246162632431373830363136246e65775f6e3133363433}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2435160 1676360
odb::dbWireEncoder_addRect $enc 0 0 900 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {24666c617474656e66756e6374696f6e5f756e69742e246162632431373830363136246e65775f6e32303038}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2435160 2383920
odb::dbWireEncoder_addRect $enc 0 0 900 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {24666c617474656e66756e6374696f6e5f756e69742e246162632431373830363136246e65775f6e32323837}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2391840 2420320
odb::dbWireEncoder_addRect $enc 0 0 900 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {24666c617474656e66756e6374696f6e5f756e69742e246162632431373830363136246e65775f6e33303332}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2433460 2235310
odb::dbWireEncoder_addRect $enc 0 0 110 1260
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {24666c617474656e66756e6374696f6e5f756e69742e246162632431373830363136246e65775f6e37353533}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2232240 1077370
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {24666c617474656e66756e6374696f6e5f756e69742e246162632431373830363136246e65775f6e383335}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2275940 1306410
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {24666c617474656e66756e6374696f6e5f756e69742e246162632431373830363136246e65775f6e38343832}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2395640 1240890
odb::dbWireEncoder_addRect $enc 0 0 900 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {636c6b6e65745f6c6561665f333039315f636c6b}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1956740 175210
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {66756e6374696f6e5f756e69742e66726163315b305d5b325d}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2475440 1358770
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
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {696e7075745f6d656d5b3136305d5b385d}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1797140 362530
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {696e7075745f6d656d5b3232385d5b335d}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2156240 125370
odb::dbWireEncoder_addRect $enc 0 0 520 70
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
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e6574313030323930}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 600140 2247560
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e6574313030333938}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2192340 253050
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e6574313031363033}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 995340 175560
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e6574313031383131}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2391840 1168720
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e6574313031393630}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2152440 964600
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e6574313032323434}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1274640 695450
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e6574313032363233}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 440540 642320
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
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e6574313032373633}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1916840 567000
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e6574313032373934}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2357860 636230
odb::dbWireEncoder_addRect $enc 0 0 90 700
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e6574313034313532}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1952940 362880
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1868420 320950
odb::dbWireEncoder_addRect $enc 0 0 90 420
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e6574313034323232}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 436740 2453850
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e6574313034323630}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 599760 1706880
odb::dbWireEncoder_addRect $enc 0 0 900 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e6574313034343034}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 237240 169050
odb::dbWireEncoder_addRect $enc 0 0 1280 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e6574313034343337}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 755940 241850
odb::dbWireEncoder_addRect $enc 0 0 900 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e6574313034353735}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2395260 242200
odb::dbWireEncoder_addRect $enc 0 0 900 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e6574313034363434}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1474140 2000250
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e6574313034363439}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1358240 2031120
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e6574313034373333}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2351940 1527890
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e6574313034393935}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1354440 499800
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e6574313035383333}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2391840 1581160
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e6574313036313439}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2471640 902650
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e6574313037353730}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 117540 2084250
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e6574313038353535}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 999140 1603210
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e6574313130303036}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 959540 1358070
odb::dbWireEncoder_addRect $enc 0 0 10 700
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e6574313130303333}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 679940 2325610
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
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e6574313131323837}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2072640 1977850
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e6574313132303434}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 519960 2140600
odb::dbWireEncoder_addRect $enc 0 0 900 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e6574313135313039}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1716960 1871450
odb::dbWireEncoder_addRect $enc 0 0 900 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e6574313135393730}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 835740 1242080
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e6574313136323636}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 277140 157850
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e6574313137383835}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1438040 779800
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e6574313233373438}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 520340 1073520
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e6574313233393730}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 835740 369810
odb::dbWireEncoder_addRect $enc 0 0 900 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e6574313234303333}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1708820 636230
odb::dbWireEncoder_addRect $enc 0 0 90 420
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e6574313434343036}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 77640 1130920
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e6574313536393831}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1354440 1100610
odb::dbWireEncoder_addRect $enc 0 0 900 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e6574313539313632}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 157440 1240610
odb::dbWireEncoder_addRect $enc 0 0 1280 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e6574313737373131}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2112540 932960
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e6574313739323331}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 436740 2207240
odb::dbWireEncoder_addRect $enc 0 0 190 70
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 436740 2207240
odb::dbWireEncoder_addRect $enc 0 0 190 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e6574313831363932}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1677440 1303120
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
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e65743733393839}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 117540 1569400
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
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e65743734343839}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1793340 2359000
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
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e65743735333033}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 915540 1846320
odb::dbWireEncoder_addRect $enc 0 0 900 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e65743735333932}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 400260 1515920
odb::dbWireEncoder_addRect $enc 0 0 900 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e65743735383132}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1637540 2154320
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1637540 2160130
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e65743735383935}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 161240 2311120
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e65743736313736}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 77640 1174320
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e65743736333636}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2032740 2005080
odb::dbWireEncoder_addRect $enc 0 0 900 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e65743736353131}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2112540 2445730
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
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e65743736383334}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 440540 1676290
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e65743737323635}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1154940 1930530
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e65743737343533}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 201140 1482040
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 396840 1639120
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e65743737343930}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 356940 1528450
odb::dbWireEncoder_addRect $enc 0 0 190 70
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 356940 1528450
odb::dbWireEncoder_addRect $enc 0 0 190 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e65743738393930}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1633740 2058560
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e65743739343230}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1278440 2074170
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e65743739343436}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1277680 1376480
odb::dbWireEncoder_addRect $enc 0 0 1280 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e65743739373339}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1793340 1532720
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e65743739373834}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1358240 1566320
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e65743830303937}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1597640 1385720
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e65743830313936}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 320840 2336810
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e65743831303937}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 640040 1375850
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e65743832393134}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2076440 2236010
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e65743832393334}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1075140 2332330
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e65743833353037}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 436740 1569610
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e65743834343339}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1553940 2411570
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
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e65743835343637}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 77640 415240
odb::dbWireEncoder_addRect $enc 0 0 900 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e65743835353338}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 197340 157850
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e65743836383930}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 237240 1371440
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e65743837353935}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1438040 1827210
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e65743837363037}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1514040 2009280
odb::dbWireEncoder_addRect $enc 0 0 900 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e65743838333938}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 77640 1264410
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e65743839303632}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1317580 1931160
odb::dbWireEncoder_addRect $enc 0 0 1280 70
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
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e65743839323832}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1916460 2023210
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
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e65743839373632}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1048650 1514030
odb::dbWireEncoder_addRect $enc 0 0 80 420
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e65743839383332}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 277140 2207450
odb::dbWireEncoder_addRect $enc 0 0 900 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e65743930333131}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2112540 2329250
odb::dbWireEncoder_addRect $enc 0 0 520 70
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
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e65743931313037}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1154940 1360730
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e65743931333636}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1713540 54880
odb::dbWireEncoder_addRect $enc 0 0 900 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e65743931383635}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 320840 2416120
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e65743932383638}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1394340 2280880
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e65743933333032}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1234740 2411570
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e65743935323634}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 875640 1403570
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e65743935363037}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 317040 1711640
odb::dbWireEncoder_addRect $enc 0 0 1280 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e65743935363736}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 600140 2117570
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e65743935383732}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2431740 406560
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e65743936323330}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 995340 145880
odb::dbWireEncoder_addRect $enc 0 0 840 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e65743936353933}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1477940 939890
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e65743937373130}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1398140 1088010
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e65743937373237}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1434240 1253280
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e65743937373334}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1713540 887880
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e65743937393239}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2355740 897400
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e65743937393536}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2312040 1972810
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e65743937393834}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2355740 2072280
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
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e65743938333436}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 835740 108570
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e65743938363338}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 520700 877730
odb::dbWireEncoder_addRect $enc 0 0 160 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e65743938393930}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2196140 1409240
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e65743939333833}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2152440 141400
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e65743939343335}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1836660 665210
odb::dbWireEncoder_addRect $enc 0 0 900 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6f706572616e645f615b375d5b32395d}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 835740 872130
odb::dbWireEncoder_addRect $enc 0 0 190 70
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
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6f706572616e645f625b365d5b32345d}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1035240 1121400
odb::dbWireEncoder_addRect $enc 0 0 900 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6f75747075745f6d656d5b3132345d5b31335d}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 719840 2042320
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6f75747075745f6d656d5b3136345d5b31355d}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2351940 1531880
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6f75747075745f6d656d5b3136375d5b32305d}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2196140 1482320
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6f75747075745f6d656d5b3137355d5b32355d}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1633740 1563730
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6f75747075745f6d656d5b3138305d5b31325d}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1952940 1553160
odb::dbWireEncoder_addRect $enc 0 0 520 70
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
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6f75747075745f6d656d5b34385d5b32375d}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 50170 1833230
odb::dbWireEncoder_addRect $enc 0 0 110 700
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6f75747075745f6d656d5b37365d5b395d}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 161240 2393720
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6f75747075745f6d656d5b375d5b32385d}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 879270 1597750
odb::dbWireEncoder_addRect $enc 0 0 50 420
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6f75747075745f6d656d5b39345d5b375d}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 320460 1975680
odb::dbWireEncoder_addRect $enc 0 0 900 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6f75747075745f6d656d5b39365d5b31355d}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1119160 2471000
odb::dbWireEncoder_addRect $enc 0 0 200 70
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1119160 2471000
odb::dbWireEncoder_addRect $enc 0 0 200 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6f75747075745f6d656d5b39365d5b345d}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 955440 2280600
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6f75747075745f6d656d5b39385d5b32395d}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 999140 1969520
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {706f696e745f726f756e6465645b325d5b38325d}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1876940 922530
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {706f696e745f746f74616c5b345d5b39305d}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1557740 718760
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
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {7371756172655f706169725b325d5b33365d}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1194840 779450
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
write_db corner-candidate.odb
write_def corner-candidate.def
drt::check_drc_cmd corner-native-drc.rpt 0 0 0 0 native_whole_drc
