namespace eval ::cR4 {
set tech [[ord::get_db] getTech]
set b [ord::get_db_block]
set target [$b findNet {services.engine\[2\].genblk1.recurrent.leaf.cmd_data\[167\]}]
if {$target eq "NULL"} {error "Missing exact source net"}
odb::dbWire_destroy [$target getWire]
set w [odb::dbWire_create $target]
set e [odb::new_dbWireEncoder]
$e begin $w
$e newPath [$tech findLayer metal8] ROUTED
$e addPoint 1267390 1033740
$e addPoint 1267390 1036940
$e newPath [$tech findLayer metal8] ROUTED
$e addPoint 1374590 1035340
$e addPoint 1374590 1065740
$e newPath [$tech findLayer metal8] ROUTED
$e addPoint 1233790 1033740
$e addPoint 1233790 1036940
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 920190 1036940
$e addPoint 1233790 1036940
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 1233790 1033740
$e addPoint 1267390 1033740
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 1345200 1035340
$e addPoint 1374590 1035340
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 1345200 1035340
$e addPoint 1345200 1036940
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 1267390 1036940
$e addPoint 1345200 1036940
$e newPath [$tech findLayer metal8] ROUTED
$e addPoint 918590 946200
$e addPoint 920190 946200
$e newPath [$tech findLayer metal8] ROUTED
$e addPoint 920190 946200
$e addPoint 920190 1036940
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 2080190 1065740
$e addPoint 2080190 1067340
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 2080190 1067340
$e addPoint 2084990 1067340
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 2084990 1065740
$e addPoint 2084990 1067340
$e newPath [$tech findLayer metal6] ROUTED
$e addPoint 2149470 1060780
$e addPoint 2149470 1065740
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 2147790 1060780
$e addPoint 2149470 1060780
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2147790 1060780
$e addPoint 2149470 1060780
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2149470 1057140
$e addPoint 2149470 1060780
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2149470 1057140
$e addPoint 2149850 1057140
$e newPath [$tech findLayer metal8] ROUTED
$e addPoint 203390 1008900
$e addPoint 204990 1008900
$e newPath [$tech findLayer metal8] ROUTED
$e addPoint 204990 918540
$e addPoint 204990 1008900
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 204990 918540
$e addPoint 649800 918540
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 649800 918540
$e addPoint 649800 920140
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 769500 918540
$e addPoint 769500 920140
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 649800 920140
$e addPoint 769500 920140
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 769500 918540
$e addPoint 918590 918540
$e newPath [$tech findLayer metal8] ROUTED
$e addPoint 918590 918540
$e addPoint 918590 946200
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 1374590 1065740
$e addPoint 2080190 1065740
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 2084990 1065740
$e addPoint 2149470 1065740
$e newPath [$tech findLayer metal8] ROUTED
$e addPoint 203390 1008900
$e addPoint 203390 1056140
$e newPath [$tech findLayer metal8] ROUTED
$e addPoint 185790 1056140
$e addPoint 185790 1062540
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 185790 1056140
$e addPoint 203390 1056140
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 1267390 1033740
set v [$b findVia {via7_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via7_0}]}
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 1267390 1036940
set v [$b findVia {via7_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via7_0}]}
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 1374590 1035340
set v [$b findVia {via7_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via7_0}]}
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 1374590 1065740
set v [$b findVia {via7_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via7_0}]}
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 920190 1036940
set v [$b findVia {via7_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via7_0}]}
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 1233790 1036940
set v [$b findVia {via7_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via7_0}]}
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 1233790 1033740
set v [$b findVia {via7_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via7_0}]}
$e newPath [$tech findLayer metal6] ROUTED
$e addPoint 2149470 1065740
set v [$b findVia {via6_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via6_0}]}
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 2149470 1060780
set v [$b findVia {via5_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via5_0}]}
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2147790 1060780
set v [$b findVia {via3_2}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via3_2}]}
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 2147790 1060780
set v [$b findVia {via4_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via4_0}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2149470 1060780
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal1] ROUTED
$e addPoint 2149850 1057140
set v [$b findVia {via1_4}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via1_4}]}
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 204990 918540
set v [$b findVia {via7_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via7_0}]}
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 918590 918540
set v [$b findVia {via7_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via7_0}]}
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 203390 1056140
set v [$b findVia {via7_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via7_0}]}
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 185790 1056140
set v [$b findVia {via7_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via7_0}]}
$e newPath [$tech findLayer metal8] ROUTED
$e addPoint 185790 1062540
set v [$b findVia {via8_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via8_0}]}
$e newPath [$tech findLayer metal9] ROUTED
$e addPoint 185790 1062540
set v [$b findVia {via9_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via9_0}]}
$e newPath [$tech findLayer metal10] ROUTED
$e addPoint 185790 1062540
$e addPoint 195390 1062540
$e newPath [$tech findLayer metal10] ROUTED
$e addPoint 195390 1061720
$e addPoint 195390 1062540
$e newPath [$tech findLayer metal10] ROUTED
$e addPoint 195390 1061720
$e addPoint 201790 1061720
$e newPath [$tech findLayer metal10] ROUTED
$e addPoint 201790 1061720
$e addPoint 201790 1064000 0
$e end
odb::delete_dbWireEncoder $e
set target [$b findNet {services.engine\[2\].genblk1.recurrent.leaf.cmd_data\[202\]}]
if {$target eq "NULL"} {error "Missing exact source net"}
odb::dbWire_destroy [$target getWire]
set w [odb::dbWire_create $target]
set e [odb::new_dbWireEncoder]
$e begin $w
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 666900 1163340
$e addPoint 666900 1164940
$e newPath [$tech findLayer metal8] ROUTED
$e addPoint 827390 1163340
$e addPoint 827390 1166540
$e newPath [$tech findLayer metal8] ROUTED
$e addPoint 907390 1163340
$e addPoint 907390 1166540
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 827390 1166540
$e addPoint 907390 1166540
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 1265400 1163340
$e addPoint 1265400 1164940
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 1473790 1163340
$e addPoint 1473790 1164940
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 1265400 1164940
$e addPoint 1473790 1164940
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 1473790 1163340
$e addPoint 1544700 1163340
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 1544700 1163340
$e addPoint 1544700 1164940
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 907390 1163340
$e addPoint 1265400 1163340
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 2155390 1144140
$e addPoint 2155390 1145740
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 666900 1163340
$e addPoint 827390 1163340
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 2170190 1144140
$e addPoint 2170190 1147340
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 2155390 1144140
$e addPoint 2170190 1144140
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 2154600 1145740
$e addPoint 2155390 1145740
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 2149470 1144780
$e addPoint 2149470 1145740
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 2149470 1144780
$e addPoint 2150590 1144780
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 2150590 1144140
$e addPoint 2150590 1144780
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 2150590 1144140
$e addPoint 2153390 1144140
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 2153390 1144140
$e addPoint 2153390 1144220
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 2153390 1144220
$e addPoint 2154600 1144220
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 2154600 1144220
$e addPoint 2154600 1145740
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2149090 1162420
$e addPoint 2149090 1163540
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2149090 1162420
$e addPoint 2152510 1162420
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2152510 1160460
$e addPoint 2152510 1162420
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2151370 1160460
$e addPoint 2152510 1160460
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2151370 1159900
$e addPoint 2151370 1160460
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2151370 1154300
$e addPoint 2151370 1159900
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2151370 1154300
$e addPoint 2154510 1154300
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 2154510 1153180
$e addPoint 2154510 1154300
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 2154510 1153180
$e addPoint 2170190 1153180
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2148710 1163540
$e addPoint 2149090 1163540
$e newPath [$tech findLayer metal6] ROUTED
$e addPoint 2170190 1147340
$e addPoint 2170190 1153180
$e newPath [$tech findLayer metal8] ROUTED
$e addPoint 2080190 1160140
$e addPoint 2080190 1164940
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 2080190 1160140
$e addPoint 2092990 1160140
$e newPath [$tech findLayer metal8] ROUTED
$e addPoint 2092990 1160140
$e addPoint 2097790 1160140
$e newPath [$tech findLayer metal8] ROUTED
$e addPoint 2097790 1145740
$e addPoint 2097790 1160140
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 1544700 1164940
$e addPoint 2080190 1164940
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 2097790 1145740
$e addPoint 2149470 1145740
$e newPath [$tech findLayer metal8] ROUTED
$e addPoint 185790 1148940
$e addPoint 185790 1164940
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 185790 1164940
$e addPoint 666900 1164940
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 827390 1163340
set v [$b findVia {via7_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via7_0}]}
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 827390 1166540
set v [$b findVia {via7_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via7_0}]}
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 907390 1166540
set v [$b findVia {via7_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via7_0}]}
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 907390 1163340
set v [$b findVia {via7_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via7_0}]}
$e newPath [$tech findLayer metal1] ROUTED
$e addPoint 2148710 1163540
set v [$b findVia {via1_4}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via1_4}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2148710 1163540
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal6] ROUTED
$e addPoint 2170190 1147340
set v [$b findVia {via6_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via6_0}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2152510 1162420
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2152510 1160460
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2151370 1159900
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2151370 1154300
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2154510 1154300
set v [$b findVia {via3_2}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via3_2}]}
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 2154510 1154300
set v [$b findVia {via4_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via4_0}]}
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 2170190 1153180
set v [$b findVia {via5_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via5_0}]}
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 2080190 1164940
set v [$b findVia {via7_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via7_0}]}
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 2080190 1160140
set v [$b findVia {via7_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via7_0}]}
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 2092990 1160140
set v [$b findVia {via7_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via7_0}]}
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 2097790 1145740
set v [$b findVia {via7_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via7_0}]}
$e newPath [$tech findLayer metal8] ROUTED
$e addPoint 185790 1148940
set v [$b findVia {via8_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via8_0}]}
$e newPath [$tech findLayer metal9] ROUTED
$e addPoint 185790 1148940
set v [$b findVia {via9_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via9_0}]}
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 185790 1164940
set v [$b findVia {via7_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via7_0}]}
$e newPath [$tech findLayer metal10] ROUTED
$e addPoint 185790 1145740
$e addPoint 185790 1148940
$e newPath [$tech findLayer metal10] ROUTED
$e addPoint 185790 1145740
$e addPoint 195390 1145740
$e newPath [$tech findLayer metal10] ROUTED
$e addPoint 195390 1145740
$e addPoint 195390 1146560
$e newPath [$tech findLayer metal10] ROUTED
$e addPoint 195390 1146560
$e addPoint 201790 1146560
$e newPath [$tech findLayer metal10] ROUTED
$e addPoint 201790 1144140 0
$e addPoint 201790 1146560
$e end
odb::delete_dbWireEncoder $e
set target [$b findNet {services.engine\[2\].genblk1.recurrent.leaf.cmd_data\[20\]}]
if {$target eq "NULL"} {error "Missing exact source net"}
odb::dbWire_destroy [$target getWire]
set w [odb::dbWire_create $target]
set e [odb::new_dbWireEncoder]
$e begin $w
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 132810 1262940
$e addPoint 132810 1264340
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 131100 1262940
$e addPoint 132810 1262940
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 131100 1261540
$e addPoint 131100 1262940
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 122170 1261540
$e addPoint 131100 1261540
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 122170 1260420
$e addPoint 122170 1261540
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 120590 1260420
$e addPoint 122170 1260420
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 120590 1260140
$e addPoint 120590 1260420
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 120030 1271340
$e addPoint 121150 1271340
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 121150 1268820
$e addPoint 121150 1271340
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 120590 1268820
$e addPoint 121150 1268820
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 120590 1261540
$e addPoint 120590 1268820
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 120590 1261540
$e addPoint 122170 1261540
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 120590 1248300
$e addPoint 120590 1260140
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 120590 1248300
$e addPoint 121150 1248300
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 120030 1280020
$e addPoint 129770 1280020
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 129770 1280020
$e addPoint 129770 1283660
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 129130 1283660
$e addPoint 129770 1283660
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 120030 1271340
$e addPoint 120030 1280020
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 121150 1164940
$e addPoint 121150 1248300
$e newPath [$tech findLayer metal9] ROUTED
$e addPoint 160190 1164940
$e addPoint 185790 1164940
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 121150 1164940
$e addPoint 160190 1164940
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 132810 1262940
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal1] ROUTED
$e addPoint 132810 1264340
set v [$b findVia {via1_4}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via1_4}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 122170 1261540
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 122170 1260420
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 120590 1260140
set v [$b findVia {via3_2}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via3_2}]}
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 120030 1271340
set v [$b findVia {via3_2}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via3_2}]}
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 121150 1271340
set v [$b findVia {via3_2}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via3_2}]}
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 120590 1261540
set v [$b findVia {via3_2}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via3_2}]}
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 120030 1280020
set v [$b findVia {via3_2}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via3_2}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 129770 1280020
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal1] ROUTED
$e addPoint 129130 1283660
set v [$b findVia {via1_4}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via1_4}]}
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 121150 1164940
set v [$b findVia {via4_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via4_0}]}
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 121150 1164940
set v [$b findVia {via5_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via5_0}]}
$e newPath [$tech findLayer metal6] ROUTED
$e addPoint 121150 1164940
set v [$b findVia {via6_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via6_0}]}
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 160190 1164940
set v [$b findVia {via7_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via7_0}]}
$e newPath [$tech findLayer metal8] ROUTED
$e addPoint 160190 1164940
set v [$b findVia {via8_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via8_0}]}
$e newPath [$tech findLayer metal9] ROUTED
$e addPoint 185790 1164940
set v [$b findVia {via9_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via9_0}]}
$e newPath [$tech findLayer metal10] ROUTED
$e addPoint 185790 1161740
$e addPoint 185790 1164940
$e newPath [$tech findLayer metal10] ROUTED
$e addPoint 185790 1161740
$e addPoint 195390 1161740
$e newPath [$tech findLayer metal10] ROUTED
$e addPoint 195390 1157720
$e addPoint 195390 1161740
$e newPath [$tech findLayer metal10] ROUTED
$e addPoint 195390 1157720
$e addPoint 201790 1157720
$e newPath [$tech findLayer metal10] ROUTED
$e addPoint 201790 1157720
$e addPoint 201790 1160000 0
$e end
odb::delete_dbWireEncoder $e
set target [$b findNet {i289_actual_v28_i8_h50_iso24_source}]
if {$target eq "NULL"} {error "Missing exact source net"}
odb::dbWire_destroy [$target getWire]
set w [odb::dbWire_create $target]
set e [odb::new_dbWireEncoder]
$e begin $w
$e newPath [$tech findLayer metal6] ROUTED
$e addPoint 136270 776140
$e addPoint 136270 776300
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 136270 776300
$e addPoint 136270 777140
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 134710 777140
$e addPoint 136270 777140
$e newPath [$tech findLayer metal8] ROUTED
$e addPoint 192190 774540
$e addPoint 192190 776140
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 136270 776140
$e addPoint 192190 776140
$e newPath [$tech findLayer metal6] ROUTED
$e addPoint 136270 776140
set v [$b findVia {via6_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via6_0}]}
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 136270 776300
set v [$b findVia {via4_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via4_0}]}
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 136270 776300
set v [$b findVia {via5_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via5_0}]}
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 136270 777140
set v [$b findVia {via3_2}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via3_2}]}
$e newPath [$tech findLayer metal1] ROUTED
$e addPoint 134710 777140
set v [$b findVia {via1_4}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via1_4}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 134710 777140
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 192190 776140
set v [$b findVia {via7_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via7_0}]}
$e newPath [$tech findLayer metal8] ROUTED
$e addPoint 192190 774540
set v [$b findVia {via8_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via8_0}]}
$e newPath [$tech findLayer metal9] ROUTED
$e addPoint 192190 774540
set v [$b findVia {via9_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via9_0}]}
$e newPath [$tech findLayer metal10] ROUTED
$e addPoint 192190 774540
$e addPoint 195390 774540
$e newPath [$tech findLayer metal10] ROUTED
$e addPoint 195390 774540
$e addPoint 195390 778560
$e newPath [$tech findLayer metal10] ROUTED
$e addPoint 195390 778560
$e addPoint 201790 778560
$e newPath [$tech findLayer metal10] ROUTED
$e addPoint 201790 776140 0
$e addPoint 201790 778560
$e end
odb::delete_dbWireEncoder $e
}
