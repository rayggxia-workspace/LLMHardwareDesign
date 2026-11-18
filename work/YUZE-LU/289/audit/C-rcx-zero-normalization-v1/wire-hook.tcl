namespace eval ::c_zero_normalization {
set tech [[ord::get_db] getTech]
set block [ord::get_db_block]
set target [$block findNet {services.engine\[1\].b\[15\]}]
if {$target eq "NULL" || [$target getWire] eq "NULL"} {error "Exact target net/wire missing"}
odb::dbWire_destroy [$target getWire]
set w [odb::dbWire_create $target]
set e [odb::new_dbWireEncoder]
$e begin $w
$e newPath [$tech findLayer metal8] ROUTED
$e addPoint 3420990 1417740
$e addPoint 3420990 1424140
$e newPath [$tech findLayer metal8] ROUTED
$e addPoint 3395390 1417740
$e addPoint 3395390 1424140
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 3395390 1417740
$e addPoint 3420990 1417740
$e newPath [$tech findLayer metal9] ROUTED
$e addPoint 3254590 1424140
$e addPoint 3395390 1424140
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 3539950 1424140
$e addPoint 3542590 1424140
$e newPath [$tech findLayer metal6] ROUTED
$e addPoint 3539950 1424140
$e addPoint 3539950 1424780
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 3539950 1424780
$e addPoint 3541630 1424780
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 3541630 1424780
$e addPoint 3541630 1425900
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 3541630 1425900
$e addPoint 3541630 1447740
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3541630 1447740
$e addPoint 3547790 1447740
$e newPath [$tech findLayer metal9] ROUTED
$e addPoint 3420990 1424140
$e addPoint 3542590 1424140
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3542190 1476300
$e addPoint 3542550 1476300
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 3542190 1471820
$e addPoint 3542190 1476300
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3542190 1471820
$e addPoint 3547110 1471820
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3547110 1466220
$e addPoint 3547110 1471820
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3547110 1466220
$e addPoint 3547790 1466220
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3547790 1465660
$e addPoint 3547790 1466220
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3547790 1465660
$e addPoint 3548910 1465660
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 3548910 1448300
$e addPoint 3548910 1465660
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3547790 1448300
$e addPoint 3548910 1448300
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3534190 1477140
$e addPoint 3534350 1477140
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3534350 1476300
$e addPoint 3534350 1477140
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3534350 1476300
$e addPoint 3542190 1476300
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 3547790 1447740
$e addPoint 3547790 1448300
$e newPath [$tech findLayer metal10] ROUTED
$e addPoint 3254590 1424140
$e addPoint 3254590 1436400
$e newPath [$tech findLayer metal10] ROUTED
$e addPoint 3254590 1436400
$e addPoint 3257790 1436400
$e newPath [$tech findLayer metal10] ROUTED
$e addPoint 3257790 1436400
$e addPoint 3257790 1449740
$e newPath [$tech findLayer metal10] ROUTED
$e addPoint 3256190 1449740
$e addPoint 3257790 1449740
$e newPath [$tech findLayer metal10] ROUTED
$e addPoint 3256190 1449740
$e addPoint 3256190 1456140 0
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 3420990 1417740
set via [$block findVia {via7_0}]
if {$via ne "NULL"} {$e addVia $via} else {$e addTechVia [$tech findVia {via7_0}]}
$e newPath [$tech findLayer metal8] ROUTED
$e addPoint 3420990 1424140
set via [$block findVia {via8_0}]
if {$via ne "NULL"} {$e addVia $via} else {$e addTechVia [$tech findVia {via8_0}]}
$e newPath [$tech findLayer metal8] ROUTED
$e addPoint 3395390 1424140
set via [$block findVia {via8_0}]
if {$via ne "NULL"} {$e addVia $via} else {$e addTechVia [$tech findVia {via8_0}]}
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 3395390 1417740
set via [$block findVia {via7_0}]
if {$via ne "NULL"} {$e addVia $via} else {$e addTechVia [$tech findVia {via7_0}]}
$e newPath [$tech findLayer metal9] ROUTED
$e addPoint 3254590 1424140
set via [$block findVia {via9_0}]
if {$via ne "NULL"} {$e addVia $via} else {$e addTechVia [$tech findVia {via9_0}]}
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 3542590 1424140
set via [$block findVia {via7_0}]
if {$via ne "NULL"} {$e addVia $via} else {$e addTechVia [$tech findVia {via7_0}]}
$e newPath [$tech findLayer metal8] ROUTED
$e addPoint 3542590 1424140
set via [$block findVia {via8_0}]
if {$via ne "NULL"} {$e addVia $via} else {$e addTechVia [$tech findVia {via8_0}]}
$e newPath [$tech findLayer metal6] ROUTED
$e addPoint 3539950 1424140
set via [$block findVia {via6_0}]
if {$via ne "NULL"} {$e addVia $via} else {$e addTechVia [$tech findVia {via6_0}]}
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 3539950 1424780
set via [$block findVia {via5_0}]
if {$via ne "NULL"} {$e addVia $via} else {$e addTechVia [$tech findVia {via5_0}]}
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 3541630 1425900
set via [$block findVia {via4_0}]
if {$via ne "NULL"} {$e addVia $via} else {$e addTechVia [$tech findVia {via4_0}]}
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3541630 1447740
set via [$block findVia {via3_2}]
if {$via ne "NULL"} {$e addVia $via} else {$e addTechVia [$tech findVia {via3_2}]}
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3547790 1447740
set via [$block findVia {via3_2}]
if {$via ne "NULL"} {$e addVia $via} else {$e addTechVia [$tech findVia {via3_2}]}
$e newPath [$tech findLayer metal1] ROUTED
$e addPoint 3542550 1476300
set via [$block findVia {via1_4}]
if {$via ne "NULL"} {$e addVia $via} else {$e addTechVia [$tech findVia {via1_4}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3542550 1476300
set via [$block findVia {via2_5}]
if {$via ne "NULL"} {$e addVia $via} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3542190 1476300
set via [$block findVia {via3_2}]
if {$via ne "NULL"} {$e addVia $via} else {$e addTechVia [$tech findVia {via3_2}]}
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3542190 1471820
set via [$block findVia {via3_2}]
if {$via ne "NULL"} {$e addVia $via} else {$e addTechVia [$tech findVia {via3_2}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3547110 1471820
set via [$block findVia {via2_5}]
if {$via ne "NULL"} {$e addVia $via} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3547110 1466220
set via [$block findVia {via2_5}]
if {$via ne "NULL"} {$e addVia $via} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3548910 1465660
set via [$block findVia {via3_2}]
if {$via ne "NULL"} {$e addVia $via} else {$e addTechVia [$tech findVia {via3_2}]}
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3548910 1448300
set via [$block findVia {via3_2}]
if {$via ne "NULL"} {$e addVia $via} else {$e addTechVia [$tech findVia {via3_2}]}
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3547790 1448300
set via [$block findVia {via3_2}]
if {$via ne "NULL"} {$e addVia $via} else {$e addTechVia [$tech findVia {via3_2}]}
$e newPath [$tech findLayer metal1] ROUTED
$e addPoint 3534190 1477140
set via [$block findVia {via1_4}]
if {$via ne "NULL"} {$e addVia $via} else {$e addTechVia [$tech findVia {via1_4}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3534190 1477140
set via [$block findVia {via2_5}]
if {$via ne "NULL"} {$e addVia $via} else {$e addTechVia [$tech findVia {via2_5}]}
$e end
odb::delete_dbWireEncoder $e
set target [$block findNet {services.store.pending_data\[73\]}]
if {$target eq "NULL" || [$target getWire] eq "NULL"} {error "Exact target net/wire missing"}
odb::dbWire_destroy [$target getWire]
set w [odb::dbWire_create $target]
set e [odb::new_dbWireEncoder]
$e begin $w
$e newPath [$tech findLayer metal8] ROUTED
$e addPoint 2534590 1038540
$e addPoint 2534590 1040140
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2283230 1037260
$e addPoint 2283310 1037260
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2283310 1037540
$e addPoint 2286670 1037540
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 2286670 1037540
$e addPoint 2286670 1037820
$e newPath [$tech findLayer metal6] ROUTED
$e addPoint 2286670 1037820
$e addPoint 2286670 1038540
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2280570 1040340
$e addPoint 2280950 1040340
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2280570 1039780
$e addPoint 2280570 1040340
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2280190 1039780
$e addPoint 2280570 1039780
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2280190 1037820
$e addPoint 2280190 1039780
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2280190 1037540
$e addPoint 2280190 1037820
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2280190 1037540
$e addPoint 2283310 1037540
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2283310 1037260
$e addPoint 2283310 1037540
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 2286670 1038540
$e addPoint 2534590 1038540
$e newPath [$tech findLayer metal10] ROUTED
$e addPoint 2534590 1040140
$e addPoint 2534590 1145700
$e newPath [$tech findLayer metal10] ROUTED
$e addPoint 2531390 1145700
$e addPoint 2534590 1145700
$e newPath [$tech findLayer metal10] ROUTED
$e addPoint 2531390 1145700
$e addPoint 2531390 1155340
$e newPath [$tech findLayer metal10] ROUTED
$e addPoint 2531390 1155340
$e addPoint 2534590 1155340
$e newPath [$tech findLayer metal10] ROUTED
$e addPoint 2534590 1155340
$e addPoint 2534590 1168140 0
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 2534590 1038540
set via [$block findVia {via7_0}]
if {$via ne "NULL"} {$e addVia $via} else {$e addTechVia [$tech findVia {via7_0}]}
$e newPath [$tech findLayer metal8] ROUTED
$e addPoint 2534590 1040140
set via [$block findVia {via8_0}]
if {$via ne "NULL"} {$e addVia $via} else {$e addTechVia [$tech findVia {via8_0}]}
$e newPath [$tech findLayer metal9] ROUTED
$e addPoint 2534590 1040140
set via [$block findVia {via9_0}]
if {$via ne "NULL"} {$e addVia $via} else {$e addTechVia [$tech findVia {via9_0}]}
$e newPath [$tech findLayer metal1] ROUTED
$e addPoint 2283230 1037260
set via [$block findVia {via1_4}]
if {$via ne "NULL"} {$e addVia $via} else {$e addTechVia [$tech findVia {via1_4}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2283230 1037260
set via [$block findVia {via2_5}]
if {$via ne "NULL"} {$e addVia $via} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2286670 1037540
set via [$block findVia {via3_2}]
if {$via ne "NULL"} {$e addVia $via} else {$e addTechVia [$tech findVia {via3_2}]}
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 2286670 1037820
set via [$block findVia {via4_0}]
if {$via ne "NULL"} {$e addVia $via} else {$e addTechVia [$tech findVia {via4_0}]}
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 2286670 1037820
set via [$block findVia {via5_0}]
if {$via ne "NULL"} {$e addVia $via} else {$e addTechVia [$tech findVia {via5_0}]}
$e newPath [$tech findLayer metal6] ROUTED
$e addPoint 2286670 1038540
set via [$block findVia {via6_0}]
if {$via ne "NULL"} {$e addVia $via} else {$e addTechVia [$tech findVia {via6_0}]}
$e newPath [$tech findLayer metal1] ROUTED
$e addPoint 2280950 1040340
set via [$block findVia {via1_4}]
if {$via ne "NULL"} {$e addVia $via} else {$e addTechVia [$tech findVia {via1_4}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2280190 1037820
set via [$block findVia {via2_5}]
if {$via ne "NULL"} {$e addVia $via} else {$e addTechVia [$tech findVia {via2_5}]}
$e end
odb::delete_dbWireEncoder $e
}
