namespace eval ::c_zero_normalization {
set tech [[ord::get_db] getTech]
set block [ord::get_db_block]
set target [$block findNet {services.engine\[2\].genblk1.recurrent.leaf.cmd_data\[232\]}]
if {$target eq "NULL" || [$target getWire] eq "NULL"} {error "Exact target net/wire missing"}
odb::dbWire_destroy [$target getWire]
set w [odb::dbWire_create $target]
set e [odb::new_dbWireEncoder]
$e begin $w
$e newPath [$tech findLayer metal9] ROUTED
$e addPoint 2089790 1212940
$e addPoint 2102590 1212940
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 2145550 1281420
$e addPoint 2146110 1281420
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 2145550 1281420
$e addPoint 2145550 1287580
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2145550 1287580
$e addPoint 2149090 1287580
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2149090 1287580
$e addPoint 2149090 1288140
$e newPath [$tech findLayer metal6] ROUTED
$e addPoint 2144430 1209180
$e addPoint 2144990 1209180
$e newPath [$tech findLayer metal6] ROUTED
$e addPoint 2144430 1206540
$e addPoint 2144430 1209180
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2149090 1294300
$e addPoint 2150590 1294300
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 2150590 1294300
$e addPoint 2150590 1297100
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2150590 1297100
$e addPoint 2154410 1297100
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2154410 1297100
$e addPoint 2154410 1297940
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2149090 1288140
$e addPoint 2149090 1294300
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 2126100 1206540
$e addPoint 2144430 1206540
$e newPath [$tech findLayer metal10] ROUTED
$e addPoint 2089790 1208140 0
$e addPoint 2089790 1212940
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 2102590 1204940
$e addPoint 2126100 1204940
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 2126100 1204940
$e addPoint 2126100 1206540
$e newPath [$tech findLayer metal8] ROUTED
$e addPoint 2102590 1204940
$e addPoint 2102590 1212940
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 2145550 1276380
$e addPoint 2146110 1276380
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 2146110 1276380
$e addPoint 2146110 1281420
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 2144990 1237740
$e addPoint 2144990 1242220
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 2144430 1242220
$e addPoint 2144990 1242220
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 2144430 1242220
$e addPoint 2144430 1243900
$e newPath [$tech findLayer metal6] ROUTED
$e addPoint 2144430 1243900
$e addPoint 2144430 1253420
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 2144430 1253420
$e addPoint 2144430 1253980
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 2144430 1253980
$e addPoint 2146110 1253980
$e newPath [$tech findLayer metal6] ROUTED
$e addPoint 2146110 1253980
$e addPoint 2146110 1256220
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 2146110 1256220
$e addPoint 2146110 1257340
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 2145550 1257340
$e addPoint 2146110 1257340
$e newPath [$tech findLayer metal6] ROUTED
$e addPoint 2145550 1257340
$e addPoint 2145550 1260700
$e newPath [$tech findLayer metal6] ROUTED
$e addPoint 2145550 1260700
$e addPoint 2146110 1260700
$e newPath [$tech findLayer metal6] ROUTED
$e addPoint 2146110 1260700
$e addPoint 2146110 1261820
$e newPath [$tech findLayer metal6] ROUTED
$e addPoint 2145550 1261820
$e addPoint 2146110 1261820
$e newPath [$tech findLayer metal6] ROUTED
$e addPoint 2144990 1209180
$e addPoint 2144990 1237740
$e newPath [$tech findLayer metal6] ROUTED
$e addPoint 2145550 1261820
$e addPoint 2145550 1276380
$e newPath [$tech findLayer metal9] ROUTED
$e addPoint 2089790 1212940
set via [$block findVia {via9_0}]
if {$via ne "NULL"} {$e addVia $via} else {$e addTechVia [$tech findVia {via9_0}]}
$e newPath [$tech findLayer metal8] ROUTED
$e addPoint 2102590 1212940
set via [$block findVia {via8_0}]
if {$via ne "NULL"} {$e addVia $via} else {$e addTechVia [$tech findVia {via8_0}]}
$e newPath [$tech findLayer metal6] ROUTED
$e addPoint 2144430 1206540
set via [$block findVia {via6_0}]
if {$via ne "NULL"} {$e addVia $via} else {$e addTechVia [$tech findVia {via6_0}]}
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 2145550 1281420
set via [$block findVia {via4_0}]
if {$via ne "NULL"} {$e addVia $via} else {$e addTechVia [$tech findVia {via4_0}]}
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2145550 1287580
set via [$block findVia {via3_2}]
if {$via ne "NULL"} {$e addVia $via} else {$e addTechVia [$tech findVia {via3_2}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2149090 1288140
set via [$block findVia {via2_5}]
if {$via ne "NULL"} {$e addVia $via} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2149090 1294300
set via [$block findVia {via2_5}]
if {$via ne "NULL"} {$e addVia $via} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2150590 1294300
set via [$block findVia {via3_2}]
if {$via ne "NULL"} {$e addVia $via} else {$e addTechVia [$tech findVia {via3_2}]}
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2150590 1297100
set via [$block findVia {via3_2}]
if {$via ne "NULL"} {$e addVia $via} else {$e addTechVia [$tech findVia {via3_2}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2154410 1297100
set via [$block findVia {via2_5}]
if {$via ne "NULL"} {$e addVia $via} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal1] ROUTED
$e addPoint 2154410 1297940
set via [$block findVia {via1_4}]
if {$via ne "NULL"} {$e addVia $via} else {$e addTechVia [$tech findVia {via1_4}]}
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 2102590 1204940
set via [$block findVia {via7_0}]
if {$via ne "NULL"} {$e addVia $via} else {$e addTechVia [$tech findVia {via7_0}]}
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 2145550 1276380
set via [$block findVia {via5_0}]
if {$via ne "NULL"} {$e addVia $via} else {$e addTechVia [$tech findVia {via5_0}]}
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 2144990 1237740
set via [$block findVia {via5_0}]
if {$via ne "NULL"} {$e addVia $via} else {$e addTechVia [$tech findVia {via5_0}]}
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 2144430 1243900
set via [$block findVia {via5_0}]
if {$via ne "NULL"} {$e addVia $via} else {$e addTechVia [$tech findVia {via5_0}]}
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 2144430 1253420
set via [$block findVia {via5_0}]
if {$via ne "NULL"} {$e addVia $via} else {$e addTechVia [$tech findVia {via5_0}]}
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 2146110 1253980
set via [$block findVia {via5_0}]
if {$via ne "NULL"} {$e addVia $via} else {$e addTechVia [$tech findVia {via5_0}]}
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 2146110 1256220
set via [$block findVia {via5_0}]
if {$via ne "NULL"} {$e addVia $via} else {$e addTechVia [$tech findVia {via5_0}]}
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 2145550 1257340
set via [$block findVia {via5_0}]
if {$via ne "NULL"} {$e addVia $via} else {$e addTechVia [$tech findVia {via5_0}]}
$e end
odb::delete_dbWireEncoder $e
set target [$block findNet {services.store.pending_data\[69\]}]
if {$target eq "NULL" || [$target getWire] eq "NULL"} {error "Exact target net/wire missing"}
odb::dbWire_destroy [$target getWire]
set w [odb::dbWire_create $target]
set e [odb::new_dbWireEncoder]
$e begin $w
$e newPath [$tech findLayer metal9] ROUTED
$e addPoint 2502590 1126540
$e addPoint 2505790 1126540
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2282850 1126300
$e addPoint 2283310 1126300
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 2283310 1126300
$e addPoint 2284990 1126300
$e newPath [$tech findLayer metal6] ROUTED
$e addPoint 2284990 1126300
$e addPoint 2284990 1126540
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2280570 1121260
$e addPoint 2280570 1122940
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2280570 1122940
$e addPoint 2281330 1122940
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2281330 1122940
$e addPoint 2281330 1126300
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2281330 1126300
$e addPoint 2282850 1126300
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 2284990 1126540
$e addPoint 2505790 1126540
$e newPath [$tech findLayer metal10] ROUTED
$e addPoint 2502590 1126540
$e addPoint 2502590 1128600
$e newPath [$tech findLayer metal10] ROUTED
$e addPoint 2502590 1128600
$e addPoint 2505790 1128600
$e newPath [$tech findLayer metal10] ROUTED
$e addPoint 2505790 1128600
$e addPoint 2505790 1157100
$e newPath [$tech findLayer metal10] ROUTED
$e addPoint 2505790 1161740
$e addPoint 2505790 1168140 0
$e newPath [$tech findLayer metal10] ROUTED
$e addPoint 2502590 1161740
$e addPoint 2505790 1161740
$e newPath [$tech findLayer metal10] ROUTED
$e addPoint 2502590 1157100
$e addPoint 2502590 1161740
$e newPath [$tech findLayer metal10] ROUTED
$e addPoint 2502590 1157100
$e addPoint 2505790 1157100
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 2505790 1126540
set via [$block findVia {via7_0}]
if {$via ne "NULL"} {$e addVia $via} else {$e addTechVia [$tech findVia {via7_0}]}
$e newPath [$tech findLayer metal8] ROUTED
$e addPoint 2505790 1126540
set via [$block findVia {via8_0}]
if {$via ne "NULL"} {$e addVia $via} else {$e addTechVia [$tech findVia {via8_0}]}
$e newPath [$tech findLayer metal9] ROUTED
$e addPoint 2502590 1126540
set via [$block findVia {via9_0}]
if {$via ne "NULL"} {$e addVia $via} else {$e addTechVia [$tech findVia {via9_0}]}
$e newPath [$tech findLayer metal1] ROUTED
$e addPoint 2282850 1126300
set via [$block findVia {via1_4}]
if {$via ne "NULL"} {$e addVia $via} else {$e addTechVia [$tech findVia {via1_4}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2282850 1126300
set via [$block findVia {via2_5}]
if {$via ne "NULL"} {$e addVia $via} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2283310 1126300
set via [$block findVia {via3_2}]
if {$via ne "NULL"} {$e addVia $via} else {$e addTechVia [$tech findVia {via3_2}]}
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 2283310 1126300
set via [$block findVia {via4_0}]
if {$via ne "NULL"} {$e addVia $via} else {$e addTechVia [$tech findVia {via4_0}]}
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 2284990 1126300
set via [$block findVia {via5_0}]
if {$via ne "NULL"} {$e addVia $via} else {$e addTechVia [$tech findVia {via5_0}]}
$e newPath [$tech findLayer metal6] ROUTED
$e addPoint 2284990 1126540
set via [$block findVia {via6_0}]
if {$via ne "NULL"} {$e addVia $via} else {$e addTechVia [$tech findVia {via6_0}]}
$e newPath [$tech findLayer metal1] ROUTED
$e addPoint 2280570 1121260
set via [$block findVia {via1_4}]
if {$via ne "NULL"} {$e addVia $via} else {$e addTechVia [$tech findVia {via1_4}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2280570 1122940
set via [$block findVia {via2_5}]
if {$via ne "NULL"} {$e addVia $via} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2281330 1122940
set via [$block findVia {via2_5}]
if {$via ne "NULL"} {$e addVia $via} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2281330 1126300
set via [$block findVia {via2_5}]
if {$via ne "NULL"} {$e addVia $via} else {$e addTechVia [$tech findVia {via2_5}]}
$e end
odb::delete_dbWireEncoder $e
}
