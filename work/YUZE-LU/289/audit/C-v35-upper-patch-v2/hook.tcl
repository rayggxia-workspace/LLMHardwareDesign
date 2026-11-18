set b [ord::get_db_block]
set tech [[ord::get_db] getTech]
set target [$b findNet {services.engine\[0\].element.e32.aperture_data\[26\]}]
if {$target eq "NULL"} {error "missing target net"}
odb::dbWire_destroy [$target getWire]
set w [odb::dbWire_create $target]
set e [odb::new_dbWireEncoder]
$e begin $w
$e newPath [$tech findLayer metal6] ROUTED
$e addPoint 3683870 1285340
$e addPoint 3683870 1287580
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 3683870 1285340
$e addPoint 3699300 1285340
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 3699300 1284780
$e addPoint 3699300 1285340
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 3779100 1286460
$e addPoint 3779100 1287020
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 3779100 1287020
$e addPoint 3780750 1287020
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 3780750 1287020
$e addPoint 3780750 1287580
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 3505230 1286460
$e addPoint 3505230 1287580
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 3505230 1286460
$e addPoint 3506350 1286460
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 3723630 1284780
$e addPoint 3723630 1286460
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 3699300 1284780
$e addPoint 3723630 1284780
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 3723630 1286460
$e addPoint 3779100 1286460
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 3905070 1329580
$e addPoint 3906750 1329580
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 3906750 1329580
$e addPoint 3906750 1333220
$e newPath [$tech findLayer metal6] ROUTED
$e addPoint 3905070 1287580
$e addPoint 3905070 1329580
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 3537710 1286460
$e addPoint 3537710 1287580
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 3506350 1286460
$e addPoint 3537710 1286460
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 3537710 1287580
$e addPoint 3683870 1287580
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 3780750 1287580
$e addPoint 3905070 1287580
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3910770 1333220
$e addPoint 3910770 1334060
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3906750 1333220
$e addPoint 3910770 1333220
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3191630 1316420
$e addPoint 3191810 1316420
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 3191630 1287580
$e addPoint 3191630 1316420
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3191810 1316420
$e addPoint 3191810 1328460
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 3191630 1287580
$e addPoint 3505230 1287580
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3923310 1333500
$e addPoint 3923310 1334060
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3910770 1334060
$e addPoint 3923310 1334060
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 4003390 1337740
$e addPoint 4008110 1337740
$e newPath [$tech findLayer metal6] ROUTED
$e addPoint 4008110 1337740
$e addPoint 4008110 1340780
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 4008110 1340780
$e addPoint 4029390 1340780
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 4029390 1340780
$e addPoint 4029390 1341340
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 4029390 1341340
$e addPoint 4043950 1341340
$e newPath [$tech findLayer metal6] ROUTED
$e addPoint 4043950 1341340
$e addPoint 4043950 1342540
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 4043950 1342540
$e addPoint 4044990 1342540
$e newPath [$tech findLayer metal8] ROUTED
$e addPoint 4044990 1342540
$e addPoint 4044990 1366540
$e newPath [$tech findLayer metal9] ROUTED
$e addPoint 4019390 1366540
$e addPoint 4044990 1366540
$e newPath [$tech findLayer metal8] ROUTED
$e addPoint 4003390 1331340
$e addPoint 4003390 1337740
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 3931390 1330140
$e addPoint 3931390 1333500
$e newPath [$tech findLayer metal6] ROUTED
$e addPoint 3931390 1330140
$e addPoint 3931390 1331340
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3923310 1333500
$e addPoint 3931390 1333500
$e newPath [$tech findLayer metal9] ROUTED
$e addPoint 3931390 1331340
$e addPoint 4003390 1331340
$e newPath [$tech findLayer metal10] ROUTED
$e addPoint 4019390 1366540
$e addPoint 4019390 1390800
$e newPath [$tech findLayer metal10] ROUTED
$e addPoint 4016190 1390800
$e addPoint 4019390 1390800
$e newPath [$tech findLayer metal10] ROUTED
$e addPoint 4051390 1484940
$e addPoint 4056190 1484940 0
$e newPath [$tech findLayer metal10] ROUTED
$e addPoint 4051390 1478540
$e addPoint 4051390 1484940
$e newPath [$tech findLayer metal10] ROUTED
$e addPoint 4016190 1390800
$e addPoint 4016190 1459360
$e newPath [$tech findLayer metal10] ROUTED
$e addPoint 4009790 1459360
$e addPoint 4016190 1459360
$e newPath [$tech findLayer metal10] ROUTED
$e addPoint 4009790 1459360
$e addPoint 4009790 1494540
$e newPath [$tech findLayer metal9] ROUTED
$e addPoint 4009790 1494540
$e addPoint 4011390 1494540
$e newPath [$tech findLayer metal8] ROUTED
$e addPoint 4011390 1494540
$e addPoint 4011390 1496140
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 4011390 1496140
$e addPoint 4024190 1496140
$e newPath [$tech findLayer metal8] ROUTED
$e addPoint 4022590 1496140
$e addPoint 4024190 1496140
$e newPath [$tech findLayer metal8] ROUTED
$e addPoint 4022590 1492940
$e addPoint 4022590 1496140
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 4022590 1492940
$e addPoint 4028990 1492940
$e newPath [$tech findLayer metal8] ROUTED
$e addPoint 4028990 1487700
$e addPoint 4028990 1492940
$e newPath [$tech findLayer metal8] ROUTED
$e addPoint 4028990 1487700
$e addPoint 4035390 1487700
$e newPath [$tech findLayer metal8] ROUTED
$e addPoint 4035390 1481740
$e addPoint 4035390 1487700
$e newPath [$tech findLayer metal9] ROUTED
$e addPoint 4035390 1481740
$e addPoint 4041300 1481740
$e newPath [$tech findLayer metal9] ROUTED
$e addPoint 4041300 1480140
$e addPoint 4041300 1481740
$e newPath [$tech findLayer metal10] ROUTED
$e addPoint 4041300 1480140
$e addPoint 4041790 1480140
$e newPath [$tech findLayer metal10] ROUTED
$e addPoint 4041790 1478540
$e addPoint 4041790 1480140
$e newPath [$tech findLayer metal10] ROUTED
$e addPoint 4041790 1478540
$e addPoint 4051390 1478540
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 3683870 1287580
set v [$b findVia {via5_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via5_0}]}
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 3683870 1285340
set v [$b findVia {via5_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via5_0}]}
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 3905070 1287580
set v [$b findVia {via5_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via5_0}]}
$e newPath [$tech findLayer metal1] ROUTED
$e addPoint 3191810 1328460
set v [$b findVia {via1_4}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via1_4}]}
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 3505230 1287580
set v [$b findVia {via4_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via4_0}]}
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 3506350 1286460
set v [$b findVia {via4_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via4_0}]}
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 3723630 1284780
set v [$b findVia {via4_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via4_0}]}
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 3723630 1286460
set v [$b findVia {via4_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via4_0}]}
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 3905070 1329580
set v [$b findVia {via5_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via5_0}]}
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 3906750 1329580
set v [$b findVia {via4_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via4_0}]}
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3906750 1333220
set v [$b findVia {via3_2}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via3_2}]}
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 3537710 1286460
set v [$b findVia {via4_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via4_0}]}
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 3537710 1287580
set v [$b findVia {via4_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via4_0}]}
$e newPath [$tech findLayer metal8] ROUTED
$e addPoint 4003390 1331340
set v [$b findVia {via8_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via8_0}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3910770 1333220
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3910770 1334060
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3191810 1316420
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3191630 1316420
set v [$b findVia {via3_2}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via3_2}]}
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 3191630 1287580
set v [$b findVia {via4_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via4_0}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3923310 1334060
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3923310 1333500
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 4003390 1337740
set v [$b findVia {via7_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via7_0}]}
$e newPath [$tech findLayer metal6] ROUTED
$e addPoint 4008110 1337740
set v [$b findVia {via6_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via6_0}]}
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 4008110 1340780
set v [$b findVia {via5_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via5_0}]}
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 4043950 1341340
set v [$b findVia {via5_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via5_0}]}
$e newPath [$tech findLayer metal6] ROUTED
$e addPoint 4043950 1342540
set v [$b findVia {via6_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via6_0}]}
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 4044990 1342540
set v [$b findVia {via7_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via7_0}]}
$e newPath [$tech findLayer metal8] ROUTED
$e addPoint 4044990 1366540
set v [$b findVia {via8_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via8_0}]}
$e newPath [$tech findLayer metal9] ROUTED
$e addPoint 4019390 1366540
set v [$b findVia {via9_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via9_0}]}
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3931390 1333500
set v [$b findVia {via3_2}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via3_2}]}
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 3931390 1330140
set v [$b findVia {via4_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via4_0}]}
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 3931390 1330140
set v [$b findVia {via5_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via5_0}]}
$e newPath [$tech findLayer metal6] ROUTED
$e addPoint 3931390 1331340
set v [$b findVia {via6_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via6_0}]}
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 3931390 1331340
set v [$b findVia {via7_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via7_0}]}
$e newPath [$tech findLayer metal8] ROUTED
$e addPoint 3931390 1331340
set v [$b findVia {via8_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via8_0}]}
$e newPath [$tech findLayer metal9] ROUTED
$e addPoint 4009790 1494540
set v [$b findVia {via9_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via9_0}]}
$e newPath [$tech findLayer metal8] ROUTED
$e addPoint 4011390 1494540
set v [$b findVia {via8_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via8_0}]}
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 4011390 1496140
set v [$b findVia {via7_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via7_0}]}
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 4024190 1496140
set v [$b findVia {via7_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via7_0}]}
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 4022590 1492940
set v [$b findVia {via7_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via7_0}]}
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 4028990 1492940
set v [$b findVia {via7_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via7_0}]}
$e newPath [$tech findLayer metal8] ROUTED
$e addPoint 4035390 1481740
set v [$b findVia {via8_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via8_0}]}
$e newPath [$tech findLayer metal9] ROUTED
$e addPoint 4041300 1480140
set v [$b findVia {via9_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via9_0}]}
$e end
odb::delete_dbWireEncoder $e
set target [$b findNet {_136204_}]
if {$target eq "NULL"} {error "missing target net"}
odb::dbWire_destroy [$target getWire]
set w [odb::dbWire_create $target]
set e [odb::new_dbWireEncoder]
$e begin $w
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3963970 2103220
$e addPoint 3966630 2103220
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3966630 2096780
$e addPoint 3966630 2103220
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3966630 2096780
$e addPoint 3967010 2096780
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3963970 2109660
$e addPoint 3964430 2109660
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 3964430 2109660
$e addPoint 3964430 2112460
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3964430 2112460
$e addPoint 3967010 2112460
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3967010 2112460
$e addPoint 3967010 2115540
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3966630 2115540
$e addPoint 3967010 2115540
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3963970 2103220
$e addPoint 3963970 2109660
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 4116730 1337140
$e addPoint 4117110 1337140
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3961690 1447460
$e addPoint 3962070 1447460
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3961690 1981700
$e addPoint 3961690 1982540
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3961690 1982540
$e addPoint 3962070 1982540
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3962070 1982540
$e addPoint 3962070 1989260
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3961690 1989260
$e addPoint 3962070 1989260
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3961690 1976660
$e addPoint 3961690 1980580
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3962450 1971900
$e addPoint 3962450 1974980
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3962450 1971900
$e addPoint 3963590 1971900
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3965870 2075500
$e addPoint 3966250 2075500
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3965870 2075500
$e addPoint 3965870 2076060
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3965870 2076060
$e addPoint 3965870 2077180
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3965870 2077180
$e addPoint 3966250 2077180
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3966250 2077180
$e addPoint 3966250 2084740
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3966250 2084740
$e addPoint 3967010 2084740
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3967010 2084740
$e addPoint 3967010 2096780
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3967010 2149420
$e addPoint 3967390 2149420
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3967010 2144660
$e addPoint 3967010 2149420
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3966630 2144660
$e addPoint 3967010 2144660
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3966630 2115540
$e addPoint 3966630 2144660
$e newPath [$tech findLayer metal9] ROUTED
$e addPoint 4227390 1356740
$e addPoint 4233790 1356740
$e newPath [$tech findLayer metal9] ROUTED
$e addPoint 4233790 1356740
$e addPoint 4233790 1356940
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3962830 1964060
$e addPoint 3963590 1964060
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3963590 1964060
$e addPoint 3963590 1971900
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 4142570 1316980
$e addPoint 4142570 1320340
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 4142570 1316980
$e addPoint 4154350 1316980
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 4154350 1316980
$e addPoint 4154350 1319220
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 4121230 2192540
$e addPoint 4121230 2193660
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 4205650 1316700
$e addPoint 4205650 1321180
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 4205650 1316700
$e addPoint 4223710 1316700
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 4223710 1316700
$e addPoint 4223710 1317260
$e newPath [$tech findLayer metal6] ROUTED
$e addPoint 4223710 1317260
$e addPoint 4223710 1318540
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 4223710 1318540
$e addPoint 4224190 1318540
$e newPath [$tech findLayer metal9] ROUTED
$e addPoint 4224190 1318540
$e addPoint 4227390 1318540
$e newPath [$tech findLayer metal10] ROUTED
$e addPoint 4227390 1318540
$e addPoint 4227390 1356740
$e newPath [$tech findLayer metal6] ROUTED
$e addPoint 4223710 2192140
$e addPoint 4223710 2193660
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 4223710 2192140
$e addPoint 4227390 2192140
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 4121230 2193660
$e addPoint 4223710 2193660
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3959950 1664740
$e addPoint 3962450 1664740
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3961310 1974980
$e addPoint 3961310 1976660
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3961310 1980580
$e addPoint 3961310 1981700
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3961310 1974980
$e addPoint 3962450 1974980
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3961310 1976660
$e addPoint 3961690 1976660
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3961310 1980580
$e addPoint 3961690 1980580
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3961310 1981700
$e addPoint 3961690 1981700
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 4032370 2215780
$e addPoint 4032750 2215780
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3961310 1530060
$e addPoint 3961310 1532860
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3959390 1532860
$e addPoint 3961310 1532860
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 3959390 1532860
$e addPoint 3959390 1555260
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3961310 1530060
$e addPoint 3961690 1530060
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3959390 1555260
$e addPoint 3967010 1555260
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 4031990 2201220
$e addPoint 4032370 2201220
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 4031990 2192540
$e addPoint 4031990 2201220
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 4031990 2192540
$e addPoint 4032190 2192540
$e newPath [$tech findLayer metal6] ROUTED
$e addPoint 4032190 2192140
$e addPoint 4032190 2192540
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 4032370 2201220
$e addPoint 4032370 2215780
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 4033510 2285700
$e addPoint 4033510 2302860
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 4032750 2285700
$e addPoint 4033510 2285700
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 4116730 1318940
$e addPoint 4120530 1318940
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 4120530 1318940
$e addPoint 4120530 1320340
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 4116730 1318940
$e addPoint 4116730 1337140
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 4120530 1320340
$e addPoint 4142570 1320340
$e newPath [$tech findLayer metal6] ROUTED
$e addPoint 4110590 2192140
$e addPoint 4110590 2192540
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 4115070 2193100
$e addPoint 4115210 2193100
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 4115070 2192540
$e addPoint 4115070 2193100
$e newPath [$tech findLayer metal9] ROUTED
$e addPoint 4032190 2192140
$e addPoint 4110590 2192140
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 4110590 2192540
$e addPoint 4121230 2192540
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 4182090 1319220
$e addPoint 4182090 1322020
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 4182090 1322020
$e addPoint 4198430 1322020
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 4198430 1321180
$e addPoint 4198430 1322020
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 4154350 1319220
$e addPoint 4182090 1319220
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 4198430 1321180
$e addPoint 4205650 1321180
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3959950 1599500
$e addPoint 3966630 1599500
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 3959950 1599500
$e addPoint 3959950 1664740
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3962390 1678180
$e addPoint 3962450 1678180
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3962390 1678180
$e addPoint 3962390 1678740
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3962070 1678740
$e addPoint 3962390 1678740
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3962070 1678740
$e addPoint 3962070 1684620
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3962070 1684620
$e addPoint 3963870 1684620
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 3963870 1684620
$e addPoint 3963870 1707300
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3963870 1707300
$e addPoint 3964350 1707300
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3962450 1664740
$e addPoint 3962450 1678180
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3966630 1757420
$e addPoint 3967230 1757420
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 3967230 1757420
$e addPoint 3968910 1757420
$e newPath [$tech findLayer metal6] ROUTED
$e addPoint 3968910 1757420
$e addPoint 3968910 1788780
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 3967230 1788780
$e addPoint 3968910 1788780
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3967010 1788780
$e addPoint 3967230 1788780
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3961630 1860740
$e addPoint 3962070 1860740
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 3961630 1842540
$e addPoint 3961630 1860740
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3961630 1842540
$e addPoint 3963590 1842540
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3959390 1921500
$e addPoint 3961690 1921500
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 3959390 1921500
$e addPoint 3959390 1948660
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3959390 1948660
$e addPoint 3962830 1948660
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3962830 1948660
$e addPoint 3962830 1964060
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3961690 1995420
$e addPoint 3962190 1995420
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 3962190 1995420
$e addPoint 3962190 2023420
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3962190 2023420
$e addPoint 3966250 2023420
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3961690 1989260
$e addPoint 3961690 1995420
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3966250 2023420
$e addPoint 3966250 2075500
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3967390 2155020
$e addPoint 3967770 2155020
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3967770 2155020
$e addPoint 3967770 2155860
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3967770 2155860
$e addPoint 3967790 2155860
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 3967790 2155020
$e addPoint 3967790 2155860
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 3967790 2155020
$e addPoint 3968350 2155020
$e newPath [$tech findLayer metal6] ROUTED
$e addPoint 3968350 2155020
$e addPoint 3968350 2192540
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3967390 2149420
$e addPoint 3967390 2155020
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 3968350 2192540
$e addPoint 4032190 2192540
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 4032750 2237620
$e addPoint 4032750 2261700
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 4032750 2215780
$e addPoint 4032750 2237620
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 4032750 2261700
$e addPoint 4032750 2285700
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3961690 1436400
$e addPoint 3961690 1447460
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3961310 1436400
$e addPoint 3961690 1436400
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3961310 1414980
$e addPoint 3961310 1436400
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3961310 1414980
$e addPoint 3961690 1414980
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3961690 1409100
$e addPoint 3961690 1414980
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3961690 1409100
$e addPoint 3962070 1409100
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3962070 1402380
$e addPoint 3962070 1409100
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3962070 1402380
$e addPoint 3963590 1402380
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3963590 1396500
$e addPoint 3963590 1402380
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3963590 1396500
$e addPoint 3964350 1396500
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3959950 1513820
$e addPoint 3961690 1513820
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3959950 1513820
$e addPoint 3959950 1514100
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3959390 1514100
$e addPoint 3959950 1514100
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 3959390 1486380
$e addPoint 3959390 1514100
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3959390 1486380
$e addPoint 3962070 1486380
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3961690 1513820
$e addPoint 3961690 1530060
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3962070 1447460
$e addPoint 3962070 1486380
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3966630 1593060
$e addPoint 3967790 1593060
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 3967790 1559740
$e addPoint 3967790 1593060
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3967010 1559740
$e addPoint 3967790 1559740
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3966630 1593060
$e addPoint 3966630 1599500
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3967010 1555260
$e addPoint 3967010 1559740
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3964350 1716540
$e addPoint 3964430 1716540
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 3963310 1716540
$e addPoint 3964430 1716540
$e newPath [$tech findLayer metal6] ROUTED
$e addPoint 3963310 1716540
$e addPoint 3963310 1755180
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 3963310 1755180
$e addPoint 3963870 1755180
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3963870 1755180
$e addPoint 3966630 1755180
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3966630 1755180
$e addPoint 3966630 1755460
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3964350 1707300
$e addPoint 3964350 1716540
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3966630 1755460
$e addPoint 3966630 1757420
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3963590 1835260
$e addPoint 3965550 1835260
$e newPath [$tech findLayer metal6] ROUTED
$e addPoint 3965550 1796620
$e addPoint 3965550 1835260
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 3965550 1796620
$e addPoint 3967230 1796620
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3967010 1796620
$e addPoint 3967230 1796620
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3963590 1835260
$e addPoint 3963590 1842540
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3967010 1788780
$e addPoint 3967010 1796620
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3961630 1915060
$e addPoint 3961690 1915060
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 3961630 1883140
$e addPoint 3961630 1915060
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3961630 1883140
$e addPoint 3962070 1883140
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3961690 1915060
$e addPoint 3961690 1921500
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3962070 1860740
$e addPoint 3962070 1883140
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3961630 1353660
$e addPoint 3962070 1353660
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 3961630 1353660
$e addPoint 3961630 1356180
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3961630 1356180
$e addPoint 3963970 1356180
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3963970 1356180
$e addPoint 3963970 1358700
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3963970 1358700
$e addPoint 3964350 1358700
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3964350 1358700
$e addPoint 3964350 1366540
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3963590 1366540
$e addPoint 3964350 1366540
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3963590 1366540
$e addPoint 3963590 1385300
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3963590 1385300
$e addPoint 3964350 1385300
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3962070 1350860
$e addPoint 3962070 1353660
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3964350 1385300
$e addPoint 3964350 1396500
$e newPath [$tech findLayer metal9] ROUTED
$e addPoint 4233790 1356940
$e addPoint 4249790 1356940
$e newPath [$tech findLayer metal10] ROUTED
$e addPoint 4249790 1356940
$e addPoint 4249790 1385740
$e newPath [$tech findLayer metal9] ROUTED
$e addPoint 4233790 1385740
$e addPoint 4249790 1385740
$e newPath [$tech findLayer metal9] ROUTED
$e addPoint 4227390 1430540
$e addPoint 4233790 1430540
$e newPath [$tech findLayer metal10] ROUTED
$e addPoint 4227390 1430540
$e addPoint 4227390 2192140
$e newPath [$tech findLayer metal10] ROUTED
$e addPoint 4233790 1385740
$e addPoint 4233790 1430540
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3963970 2103220
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3966630 2103220
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal1] ROUTED
$e addPoint 4033510 2302860
set v [$b findVia {via1_4}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via1_4}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3963970 2109660
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3964430 2109660
set v [$b findVia {via3_2}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via3_2}]}
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3964430 2112460
set v [$b findVia {via3_2}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via3_2}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3967010 2112460
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal1] ROUTED
$e addPoint 4117110 1337140
set v [$b findVia {via1_4}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via1_4}]}
$e newPath [$tech findLayer metal1] ROUTED
$e addPoint 3962070 1350860
set v [$b findVia {via1_4}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via1_4}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3962450 1664740
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3962450 1974980
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3962450 1971900
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3963590 1971900
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3965870 2076060
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3966250 2077180
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal9] ROUTED
$e addPoint 4227390 1356740
set v [$b findVia {via9_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via9_0}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3967010 1555260
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3962830 1964060
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3963590 1964060
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 4142570 1320340
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 4142570 1316980
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 4154350 1316980
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 4154350 1319220
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 4121230 2192540
set v [$b findVia {via4_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via4_0}]}
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 4121230 2193660
set v [$b findVia {via4_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via4_0}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 4205650 1321180
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 4205650 1316700
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 4223710 1316700
set v [$b findVia {via3_2}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via3_2}]}
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 4223710 1317260
set v [$b findVia {via4_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via4_0}]}
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 4223710 1317260
set v [$b findVia {via5_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via5_0}]}
$e newPath [$tech findLayer metal6] ROUTED
$e addPoint 4223710 1318540
set v [$b findVia {via6_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via6_0}]}
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 4224190 1318540
set v [$b findVia {via7_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via7_0}]}
$e newPath [$tech findLayer metal8] ROUTED
$e addPoint 4224190 1318540
set v [$b findVia {via8_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via8_0}]}
$e newPath [$tech findLayer metal9] ROUTED
$e addPoint 4227390 1318540
set v [$b findVia {via9_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via9_0}]}
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 4223710 2193660
set v [$b findVia {via5_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via5_0}]}
$e newPath [$tech findLayer metal6] ROUTED
$e addPoint 4223710 2192140
set v [$b findVia {via6_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via6_0}]}
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 4227390 2192140
set v [$b findVia {via7_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via7_0}]}
$e newPath [$tech findLayer metal8] ROUTED
$e addPoint 4227390 2192140
set v [$b findVia {via8_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via8_0}]}
$e newPath [$tech findLayer metal9] ROUTED
$e addPoint 4227390 2192140
set v [$b findVia {via9_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via9_0}]}
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3959950 1664740
set v [$b findVia {via3_2}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via3_2}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3961310 1974980
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3961310 1532860
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3959390 1532860
set v [$b findVia {via3_2}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via3_2}]}
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3959390 1555260
set v [$b findVia {via3_2}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via3_2}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 4031990 2192540
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 4032190 2192540
set v [$b findVia {via3_2}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via3_2}]}
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 4032190 2192540
set v [$b findVia {via4_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via4_0}]}
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 4032190 2192540
set v [$b findVia {via5_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via5_0}]}
$e newPath [$tech findLayer metal6] ROUTED
$e addPoint 4032190 2192140
set v [$b findVia {via6_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via6_0}]}
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 4032190 2192140
set v [$b findVia {via7_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via7_0}]}
$e newPath [$tech findLayer metal8] ROUTED
$e addPoint 4032190 2192140
set v [$b findVia {via8_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via8_0}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 4116730 1318940
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 4120530 1318940
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 4120530 1320340
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 4110590 2192540
set v [$b findVia {via5_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via5_0}]}
$e newPath [$tech findLayer metal6] ROUTED
$e addPoint 4110590 2192140
set v [$b findVia {via6_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via6_0}]}
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 4110590 2192140
set v [$b findVia {via7_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via7_0}]}
$e newPath [$tech findLayer metal8] ROUTED
$e addPoint 4110590 2192140
set v [$b findVia {via8_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via8_0}]}
$e newPath [$tech findLayer metal1] ROUTED
$e addPoint 4115210 2193100
set v [$b findVia {via1_4}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via1_4}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 4115210 2193100
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 4115070 2193100
set v [$b findVia {via3_2}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via3_2}]}
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 4115070 2192540
set v [$b findVia {via4_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via4_0}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 4182090 1319220
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 4182090 1322020
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 4198430 1322020
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 4198430 1321180
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3959950 1599500
set v [$b findVia {via3_2}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via3_2}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3966630 1599500
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3962070 1684620
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3963870 1684620
set v [$b findVia {via3_2}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via3_2}]}
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3963870 1707300
set v [$b findVia {via3_2}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via3_2}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3964350 1707300
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3966630 1757420
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3967230 1757420
set v [$b findVia {via3_2}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via3_2}]}
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 3967230 1757420
set v [$b findVia {via4_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via4_0}]}
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 3968910 1757420
set v [$b findVia {via5_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via5_0}]}
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 3968910 1788780
set v [$b findVia {via5_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via5_0}]}
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3967230 1788780
set v [$b findVia {via3_2}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via3_2}]}
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 3967230 1788780
set v [$b findVia {via4_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via4_0}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3967010 1788780
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3962070 1860740
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3961630 1860740
set v [$b findVia {via3_2}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via3_2}]}
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3961630 1842540
set v [$b findVia {via3_2}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via3_2}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3963590 1842540
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3961690 1921500
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3959390 1921500
set v [$b findVia {via3_2}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via3_2}]}
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3959390 1948660
set v [$b findVia {via3_2}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via3_2}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3962830 1948660
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3961690 1995420
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3962190 1995420
set v [$b findVia {via3_2}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via3_2}]}
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3962190 2023420
set v [$b findVia {via3_2}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via3_2}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3966250 2023420
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3967770 2155860
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3967790 2155860
set v [$b findVia {via3_2}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via3_2}]}
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 3967790 2155020
set v [$b findVia {via4_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via4_0}]}
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 3968350 2155020
set v [$b findVia {via5_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via5_0}]}
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 3968350 2192540
set v [$b findVia {via5_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via5_0}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 4032750 2237620
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 4032750 2237620
set v [$b findVia {via3_2}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via3_2}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 4032750 2261700
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 4032750 2261700
set v [$b findVia {via3_2}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via3_2}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3962070 1402380
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3963590 1402380
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3961690 1513820
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3959390 1514100
set v [$b findVia {via3_2}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via3_2}]}
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3959390 1486380
set v [$b findVia {via3_2}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via3_2}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3962070 1486380
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3966630 1593060
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3967790 1593060
set v [$b findVia {via3_2}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via3_2}]}
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3967790 1559740
set v [$b findVia {via3_2}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via3_2}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3967010 1559740
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3964350 1716540
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3964430 1716540
set v [$b findVia {via3_2}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via3_2}]}
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 3964430 1716540
set v [$b findVia {via4_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via4_0}]}
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 3963310 1716540
set v [$b findVia {via5_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via5_0}]}
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 3963310 1755180
set v [$b findVia {via5_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via5_0}]}
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3963870 1755180
set v [$b findVia {via3_2}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via3_2}]}
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 3963870 1755180
set v [$b findVia {via4_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via4_0}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3966630 1755460
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3963590 1835260
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3965550 1835260
set v [$b findVia {via3_2}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via3_2}]}
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 3965550 1835260
set v [$b findVia {via4_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via4_0}]}
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 3965550 1835260
set v [$b findVia {via5_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via5_0}]}
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 3965550 1796620
set v [$b findVia {via5_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via5_0}]}
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3967230 1796620
set v [$b findVia {via3_2}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via3_2}]}
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 3967230 1796620
set v [$b findVia {via4_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via4_0}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3967010 1796620
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3961690 1915060
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3961630 1915060
set v [$b findVia {via3_2}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via3_2}]}
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3961630 1883140
set v [$b findVia {via3_2}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via3_2}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3962070 1883140
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3962070 1353660
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3961630 1353660
set v [$b findVia {via3_2}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via3_2}]}
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3961630 1356180
set v [$b findVia {via3_2}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via3_2}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3963970 1356180
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal9] ROUTED
$e addPoint 4249790 1356940
set v [$b findVia {via9_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via9_0}]}
$e newPath [$tech findLayer metal9] ROUTED
$e addPoint 4249790 1385740
set v [$b findVia {via9_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via9_0}]}
$e newPath [$tech findLayer metal9] ROUTED
$e addPoint 4233790 1385740
set v [$b findVia {via9_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via9_0}]}
$e newPath [$tech findLayer metal9] ROUTED
$e addPoint 4227390 1430540
set v [$b findVia {via9_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via9_0}]}
$e newPath [$tech findLayer metal9] ROUTED
$e addPoint 4233790 1430540
set v [$b findVia {via9_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via9_0}]}
$e end
odb::delete_dbWireEncoder $e
