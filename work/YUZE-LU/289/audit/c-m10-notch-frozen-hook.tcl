set tech [[ord::get_db] getTech]
set b [ord::get_db_block]
set count 0
foreach n [$b getNets] {if {[$n getName] eq {dma_s_rsp_data\[52\]}} {set target $n;incr count}}
if {$count != 1} {error "nonunique target"}
odb::dbWire_destroy [$target getWire]
set w [odb::dbWire_create $target]
set e [odb::new_dbWireEncoder]
$e begin $w
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2207230 945420
$e addPoint 2209510 945420
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2379370 1191540
$e addPoint 2379370 1191820
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2379370 1191820
$e addPoint 2382430 1191820
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 2382430 1191820
$e addPoint 2382430 1192380
$e newPath [$tech findLayer metal6] ROUTED
$e addPoint 2382430 1192140
$e addPoint 2382430 1192380
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 2380990 1192140
$e addPoint 2382430 1192140
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2379750 1194060
$e addPoint 2380130 1194060
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2379750 1191820
$e addPoint 2379750 1194060
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2380130 1194060
$e addPoint 2380130 1194620
$e newPath [$tech findLayer metal8] ROUTED
$e addPoint 2380990 955340
$e addPoint 2380990 1192140
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2418130 1194060
$e addPoint 2418270 1194060
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 2418270 1193500
$e addPoint 2418270 1194060
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2418130 1194060
$e addPoint 2418130 1194620
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2380130 1194620
$e addPoint 2418130 1194620
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2209510 953260
$e addPoint 2209510 953540
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2209510 953540
$e addPoint 2211070 953540
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2211070 953260
$e addPoint 2211070 953540
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 2211070 953260
$e addPoint 2214430 953260
$e newPath [$tech findLayer metal6] ROUTED
$e addPoint 2214430 953260
$e addPoint 2214430 955340
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2209510 945420
$e addPoint 2209510 953260
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 2214430 955340
$e addPoint 2380990 955340
$e newPath [$tech findLayer metal6] ROUTED
$e addPoint 2732430 1187340
$e addPoint 2732430 1193500
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 2732430 1187340
$e addPoint 2736190 1187340
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 2418270 1193500
$e addPoint 2732430 1193500
$e newPath [$tech findLayer metal9] ROUTED
$e addPoint 2736190 1187340
$e addPoint 2787390 1187340
$e newPath [$tech findLayer metal10] ROUTED
$e addPoint 2785790 1160140 0
$e addPoint 2787390 1160140
$e newPath [$tech findLayer metal10] ROUTED
$e addPoint 2787390 1160140
$e addPoint 2787390 1187340
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 2380990 955340
set v [$b findVia {via7_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via7_0}]}
$e newPath [$tech findLayer metal1] ROUTED
$e addPoint 2207230 945420
set v [$b findVia {via1_4}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via1_4}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2207230 945420
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2209510 945420
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal1] ROUTED
$e addPoint 2379370 1191540
set v [$b findVia {via1_4}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via1_4}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2379370 1191820
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2382430 1191820
set v [$b findVia {via3_2}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via3_2}]}
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 2382430 1192380
set v [$b findVia {via4_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via4_0}]}
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 2382430 1192380
set v [$b findVia {via5_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via5_0}]}
$e newPath [$tech findLayer metal6] ROUTED
$e addPoint 2382430 1192140
set v [$b findVia {via6_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via6_0}]}
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 2380990 1192140
set v [$b findVia {via7_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via7_0}]}
$e newPath [$tech findLayer metal1] ROUTED
$e addPoint 2380130 1194060
set v [$b findVia {via1_4}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via1_4}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2379750 1191820
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2380130 1194620
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal1] ROUTED
$e addPoint 2418130 1194060
set v [$b findVia {via1_4}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via1_4}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2418130 1194060
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2418270 1194060
set v [$b findVia {via3_2}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via3_2}]}
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 2418270 1193500
set v [$b findVia {via4_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via4_0}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2418130 1194620
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2209510 953260
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2211070 953260
set v [$b findVia {via3_2}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via3_2}]}
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 2211070 953260
set v [$b findVia {via4_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via4_0}]}
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 2214430 953260
set v [$b findVia {via5_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via5_0}]}
$e newPath [$tech findLayer metal6] ROUTED
$e addPoint 2214430 955340
set v [$b findVia {via6_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via6_0}]}
$e newPath [$tech findLayer metal1] ROUTED
$e addPoint 2209510 952980
set v [$b findVia {via1_4}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via1_4}]}
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 2732430 1193500
set v [$b findVia {via5_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via5_0}]}
$e newPath [$tech findLayer metal6] ROUTED
$e addPoint 2732430 1187340
set v [$b findVia {via6_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via6_0}]}
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 2736190 1187340
set v [$b findVia {via7_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via7_0}]}
$e newPath [$tech findLayer metal8] ROUTED
$e addPoint 2736190 1187340
set v [$b findVia {via8_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via8_0}]}
$e newPath [$tech findLayer metal9] ROUTED
$e addPoint 2787390 1187340
set v [$b findVia {via9_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via9_0}]}
$e newPath [$tech findLayer metal10] ROUTED
$e addPoint 2786190 1160140
$e addPoint 2786190 1161340
$e end
odb::delete_dbWireEncoder $e
