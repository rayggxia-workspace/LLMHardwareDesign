set_thread_count 16
read_db {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/block-v1-20261101-828/tasks/revision300-final-source-r/flow/results/nangate45/bv1_block_v1_r/base/6_final.odb}
set block [ord::get_db_block]
set tech [ord::get_db_tech]
if {[$tech getManufacturingGrid]!=10} {error {Frozen grid mismatch}}
set f [open actual-grid.tsv w];puts $f "[$tech getDbUnitsPerMicron]\t[$tech getManufacturingGrid]";close $f
set exact [dict create]
foreach net [$block getNets] {set plain [string map [list [format %c 92] {}] [$net getName]];dict lappend exact $plain $net}
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {246162632433373636383330246175746f2472746c696c2e63633a333531333a4d7578476174652433333634303537}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 396840 2694160
odb::dbWireEncoder_addRect $enc 0 0 900 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {246162632433373636383330246e65775f6e333431373231}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1992840 3181850
odb::dbWireEncoder_addRect $enc 0 0 900 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {246162632433373636383330246e65775f6e343831373836}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1557740 2838360
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {246162632433373636383330246e65775f6e363339393037}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 4546440 2292640
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {246162632433373636383330246e65775f6e363833343536}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2511540 3629570
odb::dbWireEncoder_addRect $enc 0 0 900 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {246162632433373636383330246e65775f6e373835313231}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1996260 2509010
odb::dbWireEncoder_addRect $enc 0 0 900 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {62616e6b305b313433365d5b33315d}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 4550580 1873760
odb::dbWireEncoder_addRect $enc 0 0 180 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {62616e6b305b3330315d5b395d}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2714460 501760
odb::dbWireEncoder_addRect $enc 0 0 900 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {62616e6b315b313633325d5b32305d}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2192340 3630200
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {62616e6b315b313930365d5b31335d}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2355740 2725730
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {62616e6b315b3332305d5b32305d}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1354440 4360930
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {62616e6b315b3434305d5b32345d}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1078940 4467120
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {62616e6b315b3830315d5b31365d}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1238540 3876810
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {62616e6b315b3836335d5b32335d}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2993760 3070970
odb::dbWireEncoder_addRect $enc 0 0 900 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {62616e6b315b3935335d5b315d}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1636400 3089730
odb::dbWireEncoder_addRect $enc 0 0 1660 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {636c6b6e65745f6c6561665f31343838305f636c6b}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 3073940 3042410
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {636c6b6e65745f6c6561665f32303832335f636c6b}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 3153740 1340010
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {686973746f72795b32365d5b31375d}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2112540 2160130
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e6574313130303639}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 3472940 2972130
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e6574313135383634}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 679180 753970
odb::dbWireEncoder_addRect $enc 0 0 1280 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e6574313136323335}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 3540410 3509030
odb::dbWireEncoder_addRect $enc 0 0 30 420
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e6574313136353938}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1557740 3168130
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e6574313139303132}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 3708540 640640
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e6574313139363136}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2631240 2171680
odb::dbWireEncoder_addRect $enc 0 0 900 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e6574313231343537}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2272140 3545850
odb::dbWireEncoder_addRect $enc 0 0 900 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e6574313232313130}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1956360 3693970
odb::dbWireEncoder_addRect $enc 0 0 900 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e6574313234363236}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 3911840 3518200
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e6574313237383837}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 439780 729400
odb::dbWireEncoder_addRect $enc 0 0 1280 130
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e6574313238363533}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 277140 2210880
odb::dbWireEncoder_addRect $enc 0 0 900 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e6574313335383139}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 596340 1241520
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e6574313336343239}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2152440 1857240
odb::dbWireEncoder_addRect $enc 0 0 900 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e6574313339333232}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 3712340 2159850
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e6574313431303631}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2431740 583450
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e6574313433383232}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 615140 1513750
odb::dbWireEncoder_addRect $enc 0 0 130 420
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e6574313435363232}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 2431740 2628570
odb::dbWireEncoder_addRect $enc 0 0 900 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e6574313438323739}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 345780 716030
odb::dbWireEncoder_addRect $enc 0 0 70 700
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e6574313438383036}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 600140 2740010
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e6574313438383933}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 999140 3120040
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e6574313532323637}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1478260 2913610
odb::dbWireEncoder_addRect $enc 0 0 200 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e6574313537303034}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 1717340 1966090
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e6574313538373039}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 719840 2880080
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e6574313538373134}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 4107540 3900610
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e6574313539333630}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 3389340 2825690
odb::dbWireEncoder_addRect $enc 0 0 900 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e6574313731303437}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 3668640 2006200
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e6574313732353138}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal3] ROUTED
odb::dbWireEncoder_addPoint $enc 1689050 1274630
odb::dbWireEncoder_addRect $enc 0 0 30 420
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {6e6574323338393939}]]]
if {[llength $matches]!=1} {error "Ambiguous or missing target net"}
set net [lindex $matches 0]
if {[$net getWire] eq "NULL"} {error "Target wire missing"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
odb::dbWireEncoder_newPath $enc [$tech findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $enc 3748440 3399410
odb::dbWireEncoder_addRect $enc 0 0 520 70
odb::dbWireEncoder_end $enc
odb::delete_dbWireEncoder $enc
write_db corner-candidate.odb
write_def corner-candidate.def
drt::check_drc_cmd corner-native-drc.rpt 0 0 0 0 native_whole_drc
