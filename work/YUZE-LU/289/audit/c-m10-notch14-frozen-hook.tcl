set tech [[ord::get_db] getTech]
set b [ord::get_db_block]
set count 0
foreach n [$b getNets] {if {[$n getName] eq {dma_s_rsp_data\[14\]}} {set target $n;incr count}}
if {$count != 1} {error "nonunique target"}
odb::dbWire_destroy [$target getWire]
set w [odb::dbWire_create $target]
set e [odb::new_dbWireEncoder]
$e begin $w
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2312870 1210860
$e addPoint 2312990 1210860
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 2312990 1210300
$e addPoint 2312990 1210860
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2275630 1012620
$e addPoint 2278270 1012620
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2298050 1205260
$e addPoint 2298430 1205260
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 2298430 1205260
$e addPoint 2298430 1210300
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2277910 1210860
$e addPoint 2277910 1211700
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2277910 1211700
$e addPoint 2278270 1211700
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 2278270 1205260
$e addPoint 2278270 1211700
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2278270 1205260
$e addPoint 2298050 1205260
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 2278270 1012620
$e addPoint 2278270 1205260
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 2298430 1210300
$e addPoint 2312990 1210300
$e newPath [$tech findLayer metal6] ROUTED
$e addPoint 2721790 1204940
$e addPoint 2721790 1210300
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 2312990 1210300
$e addPoint 2721790 1210300
$e newPath [$tech findLayer metal10] ROUTED
$e addPoint 2736190 1158540
$e addPoint 2736190 1160140 0
$e newPath [$tech findLayer metal10] ROUTED
$e addPoint 2736000 1158540
$e addPoint 2736190 1158540
$e newPath [$tech findLayer metal10] ROUTED
$e addPoint 2736000 1155340
$e addPoint 2736000 1158540
$e newPath [$tech findLayer metal10] ROUTED
$e addPoint 2729790 1155340
$e addPoint 2736000 1155340
$e newPath [$tech findLayer metal10] ROUTED
$e addPoint 2729790 1155340
$e addPoint 2729790 1162800
$e newPath [$tech findLayer metal9] ROUTED
$e addPoint 2721790 1187340
$e addPoint 2732990 1187340
$e newPath [$tech findLayer metal10] ROUTED
$e addPoint 2732990 1162800
$e addPoint 2732990 1187340
$e newPath [$tech findLayer metal10] ROUTED
$e addPoint 2729790 1162800
$e addPoint 2732990 1162800
$e newPath [$tech findLayer metal8] ROUTED
$e addPoint 2721790 1187340
$e addPoint 2721790 1204940
$e newPath [$tech findLayer metal1] ROUTED
$e addPoint 2312870 1210860
set v [$b findVia {via1_4}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via1_4}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2312870 1210860
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2312990 1210860
set v [$b findVia {via3_2}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via3_2}]}
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 2312990 1210300
set v [$b findVia {via4_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via4_0}]}
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2278270 1012620
set v [$b findVia {via3_2}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via3_2}]}
$e newPath [$tech findLayer metal1] ROUTED
$e addPoint 2275630 1012620
set v [$b findVia {via1_4}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via1_4}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2275630 1012620
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal1] ROUTED
$e addPoint 2298050 1205260
set v [$b findVia {via1_4}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via1_4}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2298050 1205260
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2298430 1205260
set v [$b findVia {via3_2}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via3_2}]}
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 2298430 1210300
set v [$b findVia {via4_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via4_0}]}
$e newPath [$tech findLayer metal1] ROUTED
$e addPoint 2277910 1210860
set v [$b findVia {via1_4}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via1_4}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2277910 1211700
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2278270 1211700
set v [$b findVia {via3_2}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via3_2}]}
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2278270 1205260
set v [$b findVia {via3_2}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via3_2}]}
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 2721790 1210300
set v [$b findVia {via5_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via5_0}]}
$e newPath [$tech findLayer metal6] ROUTED
$e addPoint 2721790 1204940
set v [$b findVia {via6_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via6_0}]}
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 2721790 1204940
set v [$b findVia {via7_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via7_0}]}
$e newPath [$tech findLayer metal8] ROUTED
$e addPoint 2721790 1187340
set v [$b findVia {via8_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via8_0}]}
$e newPath [$tech findLayer metal9] ROUTED
$e addPoint 2732990 1187340
set v [$b findVia {via9_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via9_0}]}
$e newPath [$tech findLayer metal10] ROUTED
$e addPoint 2732990 1161340
$e addPoint 2732990 1162800
$e newPath [$tech findLayer metal10] ROUTED
$e addPoint 2732990 1161340
$e addPoint 2734990 1161340
$e end
odb::delete_dbWireEncoder $e
