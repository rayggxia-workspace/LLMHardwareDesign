set_thread_count 16
read_db {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/block-v1-20261101-828/tasks/revision300-final-source-r/flow/results/nangate45/bv1_block_v1_r/base/6_final.odb}
set block [ord::get_db_block]
set tech [ord::get_db_tech]
if {[$tech getManufacturingGrid]!=10} {error {Frozen grid mismatch}}
set f [open actual-grid.tsv w];puts $f "[$tech getDbUnitsPerMicron]\t[$tech getManufacturingGrid]";close $f
set exact [dict create]
foreach net [$block getNets] {set plain [string map [list [format %c 92] {}] [$net getName]];dict lappend exact $plain $net}
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {246162632433373636383330246e65775f6e333237393239}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1597260 3573360
odb::dbWireEncoder_addRect $enc 0 0 900 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {246162632433373636383330246e65775f6e333338383338}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1637860 3064040
odb::dbWireEncoder_addRect $enc 0 0 200 70
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1637860 3064040
odb::dbWireEncoder_addRect $enc 0 0 200 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {246162632433373636383330246e65775f6e333339313732}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2990340 1160250
odb::dbWireEncoder_addRect $enc 0 0 900 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {246162632433373636383330246e65775f6e333633313436}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 4111660 1500450
odb::dbWireEncoder_addRect $enc 0 0 200 70
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 4111660 1500450
odb::dbWireEncoder_addRect $enc 0 0 200 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {246162632433373636383330246e65775f6e343330383931}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 3910700 2444890
odb::dbWireEncoder_addRect $enc 0 0 1660 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {246162632433373636383330246e65775f6e343438363536}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 3113840 1178170
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {246162632433373636383330246e65775f6e353038383834}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 759740 2726080
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {246162632433373636383330246e65775f6e353236323332}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1278060 1871170
odb::dbWireEncoder_addRect $enc 0 0 900 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {246162632433373636383330246e65775f6e353336353331}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2112540 875000
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {246162632433373636383330246e65775f6e353338303135}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2196140 1182160
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {246162632433373636383330246e65775f6e353738393032}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1557360 2166850
odb::dbWireEncoder_addRect $enc 0 0 900 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {246162632433373636383330246e65775f6e363139353936}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 3193640 1452570
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {246162632433373636383330246e65775f6e363237383536}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 4067640 1389640
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {246162632433373636383330246e65775f6e363535373039}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 3987840 915810
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {246162632433373636383330246e65775f6e363537353238}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 4147440 809760
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {246162632433373636383330246e65775f6e373038313039}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 3474290 3832150
odb::dbWireEncoder_addRect $enc 0 0 70 420
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {246162632433373636383330246e65775f6e373132393839}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 3193640 3911250
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {246162632433373636383330246e65775f6e373337393231}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 3070740 4067630
odb::dbWireEncoder_addRect $enc 0 0 90 420
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {62616e6b305b313232345d5b32375d}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1234740 2848720
odb::dbWireEncoder_addRect $enc 0 0 1280 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {62616e6b305b313435395d5b32375d}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 676140 3015810
odb::dbWireEncoder_addRect $enc 0 0 900 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {62616e6b315b3831335d5b315d}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 3179380 3272710
odb::dbWireEncoder_addRect $enc 0 0 130 1260
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {62616e6b315b3838315d5b335d}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1238540 3397730
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {62616e6b315b3839355d5b31305d}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 3353240 3078530
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {62616e6b315b3936365d5b31385d}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 3791380 2881970
odb::dbWireEncoder_addRect $enc 0 0 1280 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {636c6b6e65745f6c6561665f32323636325f636c6b}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1477940 513730
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {636c6b6e65745f6c6561665f333733345f636c6b}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1238540 3266410
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {636c6b6e65745f6c6561665f373732315f636c6b}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1956740 4229610
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e6574313039303639}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 4310840 2824010
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e6574313130343239}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1035240 3083920
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e6574313132383236}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 3189840 1664600
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e6574313134303733}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 3389340 3860850
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e6574313135323430}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 3349440 2770530
odb::dbWireEncoder_addRect $enc 0 0 900 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e6574313137303535}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 915540 653520
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e6574313139363635}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2695290 1913030
odb::dbWireEncoder_addRect $enc 0 0 110 1260
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e6574313230383938}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1278060 3089730
odb::dbWireEncoder_addRect $enc 0 0 900 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e6574313331383832}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 3321690 879550
odb::dbWireEncoder_addRect $enc 0 0 10 420
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e6574313332373135}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 3832040 455210
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e6574313337373431}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 3269640 3104290
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e6574313337383233}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 3309540 3652810
odb::dbWireEncoder_addRect $enc 0 0 900 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e6574313338353439}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 3706090 4151350
odb::dbWireEncoder_addRect $enc 0 0 110 420
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e6574313339363030}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 3269640 1800680
odb::dbWireEncoder_addRect $enc 0 0 1280 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e6574313433393838}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 280940 3547250
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e6574313434373233}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 955440 3475010
odb::dbWireEncoder_addRect $enc 0 0 900 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e6574313435353330}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 3991640 1874530
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e6574313436363134}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 4390640 4056010
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e6574313436383938}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 4346940 955920
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e6574313438303235}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 4270940 2417520
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e6574313531343231}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1078940 4240870
odb::dbWireEncoder_addRect $enc 0 0 520 10
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e6574313533353531}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1115040 2272690
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e6574313536303735}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2465380 1274630
odb::dbWireEncoder_addRect $enc 0 0 110 420
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e6574313536373230}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1557740 485730
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e6574313537333434}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 2017380 317030
odb::dbWireEncoder_addRect $enc 0 0 90 980
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e6574313630353339}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 679940 2264010
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e6574313631323633}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 516540 2860480
odb::dbWireEncoder_addRect $enc 0 0 900 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e6574313632363735}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 4430160 1448650
odb::dbWireEncoder_addRect $enc 0 0 900 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6f706572616e645f625b305d5b32385d}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1553940 1655920
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {746170735b31335d5b31345d}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2032740 1516970
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
write_db corner-candidate.odb
write_def corner-candidate.def
drt::check_drc_cmd corner-native-drc.rpt 0 0 0 0 native_whole_drc
