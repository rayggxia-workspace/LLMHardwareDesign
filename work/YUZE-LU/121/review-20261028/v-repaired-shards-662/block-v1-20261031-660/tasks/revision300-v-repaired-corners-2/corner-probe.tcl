set_thread_count 16
read_db {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/block-v1-20261031-630/tasks/revision300-final-source-v/flow/results/nangate45/bv1_block_v1_v/base/6_final.odb}
set block [ord::get_db_block]
set tech [ord::get_db_tech]
set exact [dict create]
foreach net [$block getNets] {set plain [string map [list [format %c 92] {}] [$net getName]];dict lappend exact $plain $net}
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
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {246162632431343134303338246e65775f6e333439393135}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 117540 1941170
odb::dbWireEncoder_addRect $enc 0 0 900 70
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
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e65743733343236}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1274640 2465960
odb::dbWireEncoder_addRect $enc 0 0 900 70
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
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e65743738313433}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 995340 2318680
odb::dbWireEncoder_addRect $enc 0 0 1280 70
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
write_db corner-candidate.odb
write_def corner-candidate.def
drt::check_drc_cmd corner-native-drc.rpt 0 0 0 0 native_whole_drc
