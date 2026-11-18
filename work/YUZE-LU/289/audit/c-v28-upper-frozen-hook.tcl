set b [ord::get_db_block]
set tech [[ord::get_db] getTech]
set target [$b findNet {net118438}]
if {$target eq "NULL"} {error "missing target net"}
odb::dbWire_destroy [$target getWire]
set w [odb::dbWire_create $target]
set e [odb::new_dbWireEncoder]
$e begin $w
$e newPath [$tech findLayer metal8] ROUTED
$e addPoint 3771390 979340
$e addPoint 3771390 985740
$e newPath [$tech findLayer metal9] ROUTED
$e addPoint 3603390 988940
$e addPoint 3609790 988940
$e newPath [$tech findLayer metal9] ROUTED
$e addPoint 3603390 985740
$e addPoint 3603390 988940
$e newPath [$tech findLayer metal9] ROUTED
$e addPoint 3609790 985740
$e addPoint 3609790 988940
$e newPath [$tech findLayer metal8] ROUTED
$e addPoint 3830590 924940
$e addPoint 3830590 982540
$e newPath [$tech findLayer metal8] ROUTED
$e addPoint 3908990 921740
$e addPoint 3908990 929740
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3151910 1192380
$e addPoint 3151910 1195460
$e newPath [$tech findLayer metal9] ROUTED
$e addPoint 3260990 985740
$e addPoint 3603390 985740
$e newPath [$tech findLayer metal9] ROUTED
$e addPoint 3609790 985740
$e addPoint 3771390 985740
$e newPath [$tech findLayer metal9] ROUTED
$e addPoint 3771390 979340
$e addPoint 3779390 979340
$e newPath [$tech findLayer metal9] ROUTED
$e addPoint 3779390 979340
$e addPoint 3779390 982540
$e newPath [$tech findLayer metal9] ROUTED
$e addPoint 3779390 982540
$e addPoint 3830590 982540
$e newPath [$tech findLayer metal8] ROUTED
$e addPoint 3888190 921740
$e addPoint 3888190 924940
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 3830590 924940
$e addPoint 3888190 924940
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 3888190 921740
$e addPoint 3908990 921740
$e newPath [$tech findLayer metal8] ROUTED
$e addPoint 3940990 918540
$e addPoint 3940990 929740
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 3908990 929740
$e addPoint 3940990 929740
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2937210 1199100
$e addPoint 2937590 1199100
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2937590 1194060
$e addPoint 2937590 1199100
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3005230 1195460
$e addPoint 3005230 1196020
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3005230 1195460
$e addPoint 3035950 1195460
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3035950 1195460
$e addPoint 3035950 1195740
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3117150 1195460
$e addPoint 3117150 1196020
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3117150 1195460
$e addPoint 3151910 1195460
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3180410 1191260
$e addPoint 3180410 1192380
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3180410 1191260
$e addPoint 3184970 1191260
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3184970 1191260
$e addPoint 3184970 1191540
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3184970 1191540
$e addPoint 3186870 1191540
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3186870 1191540
$e addPoint 3186870 1195180
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3151910 1192380
$e addPoint 3180410 1192380
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 3248750 1195180
$e addPoint 3248750 1195740
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 3248750 1195740
$e addPoint 3260510 1195740
$e newPath [$tech findLayer metal6] ROUTED
$e addPoint 3260510 1195740
$e addPoint 3260510 1196940
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 3260510 1196940
$e addPoint 3260990 1196940
$e newPath [$tech findLayer metal8] ROUTED
$e addPoint 3260990 985740
$e addPoint 3260990 1196940
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2937210 1199100
$e addPoint 2937210 1208620
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2975970 1195740
$e addPoint 2990410 1195740
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2990410 1195740
$e addPoint 2991930 1195740
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2991930 1195740
$e addPoint 3003330 1195740
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3003330 1195740
$e addPoint 3003330 1196020
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3003330 1196020
$e addPoint 3005230 1196020
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3083700 1196020
$e addPoint 3117150 1196020
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3083700 1195740
$e addPoint 3083700 1196020
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3035950 1195740
$e addPoint 3083700 1195740
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3205490 1194900
$e addPoint 3205490 1195180
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3205490 1194900
$e addPoint 3215710 1194900
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 3215710 1194900
$e addPoint 3215710 1195180
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3186870 1195180
$e addPoint 3205490 1195180
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 3215710 1195180
$e addPoint 3248750 1195180
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 4004990 865740
$e addPoint 4025790 865740
$e newPath [$tech findLayer metal8] ROUTED
$e addPoint 4025790 864140
$e addPoint 4025790 865740
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2937210 1208620
$e addPoint 2975970 1208620
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2975970 1195740
$e addPoint 2975970 1208620
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 3940990 918540
$e addPoint 4001790 918540
$e newPath [$tech findLayer metal8] ROUTED
$e addPoint 4004990 865740
$e addPoint 4004990 877800
$e newPath [$tech findLayer metal8] ROUTED
$e addPoint 4001790 908940
$e addPoint 4006590 908940
$e newPath [$tech findLayer metal8] ROUTED
$e addPoint 4006590 877800
$e addPoint 4006590 908940
$e newPath [$tech findLayer metal8] ROUTED
$e addPoint 4004990 877800
$e addPoint 4006590 877800
$e newPath [$tech findLayer metal8] ROUTED
$e addPoint 4001790 908940
$e addPoint 4001790 918540
$e newPath [$tech findLayer metal8] ROUTED
$e addPoint 4033790 859340
$e addPoint 4033790 864140
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 4033790 859340
$e addPoint 4048430 859340
$e newPath [$tech findLayer metal6] ROUTED
$e addPoint 4048430 859340
$e addPoint 4048430 863100
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 4048430 863100
$e addPoint 4059630 863100
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 4059630 863100
$e addPoint 4059730 863100
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 4059350 863100
$e addPoint 4059730 863100
$e newPath [$tech findLayer metal8] ROUTED
$e addPoint 4025790 864140
$e addPoint 4033790 864140
$e newPath [$tech findLayer metal8] ROUTED
$e addPoint 3260990 985740
set v [$b findVia {via8_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via8_0}]}
$e newPath [$tech findLayer metal8] ROUTED
$e addPoint 3771390 985740
set v [$b findVia {via8_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via8_0}]}
$e newPath [$tech findLayer metal8] ROUTED
$e addPoint 3771390 979340
set v [$b findVia {via8_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via8_0}]}
$e newPath [$tech findLayer metal8] ROUTED
$e addPoint 3830590 982540
set v [$b findVia {via8_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via8_0}]}
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 3830590 924940
set v [$b findVia {via7_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via7_0}]}
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 3908990 921740
set v [$b findVia {via7_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via7_0}]}
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 3908990 929740
set v [$b findVia {via7_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via7_0}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3151910 1195460
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3151910 1192380
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 3888190 924940
set v [$b findVia {via7_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via7_0}]}
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 3888190 921740
set v [$b findVia {via7_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via7_0}]}
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 3940990 929740
set v [$b findVia {via7_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via7_0}]}
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 3940990 918540
set v [$b findVia {via7_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via7_0}]}
$e newPath [$tech findLayer metal1] ROUTED
$e addPoint 2937590 1194060
set v [$b findVia {via1_4}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via1_4}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3005230 1195460
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3180410 1192380
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3180410 1191260
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3186870 1191540
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3186870 1195180
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 3260510 1195740
set v [$b findVia {via5_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via5_0}]}
$e newPath [$tech findLayer metal6] ROUTED
$e addPoint 3260510 1196940
set v [$b findVia {via6_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via6_0}]}
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 3260990 1196940
set v [$b findVia {via7_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via7_0}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2937210 1208620
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2975970 1195740
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2990410 1195740
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2991930 1195740
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3003330 1195740
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3215710 1194900
set v [$b findVia {via3_2}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via3_2}]}
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 3215710 1195180
set v [$b findVia {via4_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via4_0}]}
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 4004990 865740
set v [$b findVia {via7_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via7_0}]}
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 4025790 865740
set v [$b findVia {via7_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via7_0}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2975970 1208620
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 4001790 918540
set v [$b findVia {via7_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via7_0}]}
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 4033790 859340
set v [$b findVia {via7_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via7_0}]}
$e newPath [$tech findLayer metal6] ROUTED
$e addPoint 4048430 859340
set v [$b findVia {via6_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via6_0}]}
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 4048430 863100
set v [$b findVia {via5_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via5_0}]}
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 4059630 863100
set v [$b findVia {via3_2}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via3_2}]}
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 4059630 863100
set v [$b findVia {via4_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via4_0}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 4059730 863100
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal1] ROUTED
$e addPoint 4059350 863100
set v [$b findVia {via1_4}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via1_4}]}
$e end
odb::delete_dbWireEncoder $e
set target [$b findNet {net73253}]
if {$target eq "NULL"} {error "missing target net"}
odb::dbWire_destroy [$target getWire]
set w [odb::dbWire_create $target]
set e [odb::new_dbWireEncoder]
$e begin $w
$e newPath [$tech findLayer metal8] ROUTED
$e addPoint 2926590 1430540
$e addPoint 2926590 1433740
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 3032590 1434300
$e addPoint 3032590 1436260
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3032590 1436260
$e addPoint 3035250 1436260
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3035250 1436260
$e addPoint 3035250 1439900
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3035250 1439900
$e addPoint 3036010 1439900
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3032590 1527540
$e addPoint 3033350 1527540
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3033350 1523620
$e addPoint 3033350 1527540
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3032590 1523620
$e addPoint 3033350 1523620
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3032590 1506820
$e addPoint 3032590 1523620
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3032590 1506820
$e addPoint 3032970 1506820
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3032970 1498980
$e addPoint 3032970 1506820
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3032970 1498980
$e addPoint 3035630 1498980
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3035630 1487780
$e addPoint 3035630 1498980
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3034110 1487780
$e addPoint 3035630 1487780
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3031830 1602860
$e addPoint 3034490 1602860
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3031830 1595860
$e addPoint 3031830 1602860
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3031830 1595860
$e addPoint 3033350 1595860
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3033350 1579060
$e addPoint 3033350 1595860
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3033350 1579060
$e addPoint 3034110 1579060
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3034110 1572340
$e addPoint 3034110 1579060
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3034110 1572340
$e addPoint 3037150 1572340
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3032210 1649620
$e addPoint 3032590 1649620
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3032590 1649620
$e addPoint 3032590 1655220
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3032210 1676780
$e addPoint 3032210 1684620
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3033730 1465380
$e addPoint 3034110 1465380
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3033730 1462020
$e addPoint 3033730 1465380
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3033730 1462020
$e addPoint 3034490 1462020
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3034490 1451940
$e addPoint 3034490 1462020
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3034490 1451940
$e addPoint 3034870 1451940
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3034870 1451100
$e addPoint 3034870 1451940
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3034870 1451100
$e addPoint 3035250 1451100
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3035250 1449420
$e addPoint 3035250 1451100
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3035250 1449420
$e addPoint 3036010 1449420
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3034110 1465380
$e addPoint 3034110 1487780
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3036010 1439900
$e addPoint 3036010 1449420
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3032590 1532300
$e addPoint 3033350 1532300
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3033350 1532300
$e addPoint 3033350 1542380
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3033350 1542380
$e addPoint 3037150 1542380
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3032590 1527540
$e addPoint 3032590 1532300
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3037150 1542380
$e addPoint 3037150 1572340
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3032210 1642340
$e addPoint 3032590 1642340
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3032590 1622180
$e addPoint 3032590 1642340
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3032590 1622180
$e addPoint 3034490 1622180
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3032210 1642340
$e addPoint 3032210 1649620
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3034490 1602860
$e addPoint 3034490 1622180
$e newPath [$tech findLayer metal9] ROUTED
$e addPoint 2865790 1430540
$e addPoint 2926590 1430540
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2982430 1426740
$e addPoint 2982430 1430100
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2982430 1430100
$e addPoint 2983870 1430100
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 2983870 1430100
$e addPoint 2983870 1430380
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 2983870 1430380
$e addPoint 2983870 1431500
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 2968750 1431500
$e addPoint 2983870 1431500
$e newPath [$tech findLayer metal6] ROUTED
$e addPoint 2968750 1431500
$e addPoint 2968750 1433740
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 2983870 1431500
$e addPoint 2983870 1434300
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 2926590 1433740
$e addPoint 2968750 1433740
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 2983870 1434300
$e addPoint 3032590 1434300
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 3040430 1684620
$e addPoint 3040430 1714580
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3036010 1714580
$e addPoint 3040430 1714580
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3032590 1676500
$e addPoint 3032590 1676780
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3032210 1676780
$e addPoint 3032590 1676780
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3032210 1684620
$e addPoint 3040430 1684620
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 3032590 1655220
$e addPoint 3032590 1676500
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 2860990 1430540
$e addPoint 2860990 1432140
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 2816190 1432140
$e addPoint 2860990 1432140
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 2860990 1430540
$e addPoint 2865790 1430540
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 2790110 1322860
$e addPoint 2790110 1324820
$e newPath [$tech findLayer metal6] ROUTED
$e addPoint 2790110 1320140
$e addPoint 2790110 1322860
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 2784190 1320140
$e addPoint 2790110 1320140
$e newPath [$tech findLayer metal8] ROUTED
$e addPoint 2784190 1320140
$e addPoint 2784190 1350540
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2820930 1320340
$e addPoint 2820930 1322020
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2812190 1322020
$e addPoint 2820930 1322020
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2790110 1324820
$e addPoint 2812190 1324820
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2812190 1309140
$e addPoint 2812190 1324820
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3036010 1723540
$e addPoint 3036770 1723540
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3036770 1723540
$e addPoint 3036770 1724100
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3036770 1724100
$e addPoint 3037150 1724100
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3037150 1724100
$e addPoint 3037150 1731100
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3037150 1731100
$e addPoint 3037530 1731100
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3036010 1714580
$e addPoint 3036010 1723540
$e newPath [$tech findLayer metal9] ROUTED
$e addPoint 2784190 1350540
$e addPoint 2787390 1350540
$e newPath [$tech findLayer metal9] ROUTED
$e addPoint 2787390 1350540
$e addPoint 2787390 1353740
$e newPath [$tech findLayer metal9] ROUTED
$e addPoint 2787390 1353740
$e addPoint 2801790 1353740
$e newPath [$tech findLayer metal8] ROUTED
$e addPoint 2801790 1353740
$e addPoint 2801790 1360140
$e newPath [$tech findLayer metal9] ROUTED
$e addPoint 2801790 1360140
$e addPoint 2806590 1360140
$e newPath [$tech findLayer metal9] ROUTED
$e addPoint 2806590 1360140
$e addPoint 2806590 1366540
$e newPath [$tech findLayer metal9] ROUTED
$e addPoint 2806590 1366540
$e addPoint 2816190 1366540
$e newPath [$tech findLayer metal8] ROUTED
$e addPoint 2816190 1366540
$e addPoint 2816190 1432140
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 2865790 1430540
set v [$b findVia {via7_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via7_0}]}
$e newPath [$tech findLayer metal8] ROUTED
$e addPoint 2865790 1430540
set v [$b findVia {via8_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via8_0}]}
$e newPath [$tech findLayer metal8] ROUTED
$e addPoint 2926590 1430540
set v [$b findVia {via8_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via8_0}]}
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 2926590 1433740
set v [$b findVia {via7_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via7_0}]}
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 3032590 1434300
set v [$b findVia {via4_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via4_0}]}
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3032590 1436260
set v [$b findVia {via3_2}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via3_2}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3035250 1436260
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3035250 1439900
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3036010 1439900
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3032590 1527540
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3033350 1527540
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3033350 1523620
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3032590 1523620
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3032970 1498980
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3035630 1498980
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3035630 1487780
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3034110 1487780
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3034490 1602860
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3031830 1602860
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3031830 1595860
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3033350 1595860
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3033350 1579060
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3034110 1579060
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3034110 1572340
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3037150 1572340
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3032590 1655220
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3032590 1655220
set v [$b findVia {via3_2}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via3_2}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3032210 1676780
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3032210 1684620
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3033730 1462020
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3034490 1462020
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3033350 1542380
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3037150 1542380
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3032590 1622180
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3034490 1622180
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 2816190 1432140
set v [$b findVia {via7_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via7_0}]}
$e newPath [$tech findLayer metal1] ROUTED
$e addPoint 2982430 1426740
set v [$b findVia {via1_4}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via1_4}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2982430 1430100
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2983870 1430100
set v [$b findVia {via3_2}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via3_2}]}
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 2983870 1430380
set v [$b findVia {via4_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via4_0}]}
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 2968750 1431500
set v [$b findVia {via5_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via5_0}]}
$e newPath [$tech findLayer metal6] ROUTED
$e addPoint 2968750 1433740
set v [$b findVia {via6_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via6_0}]}
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3040430 1684620
set v [$b findVia {via3_2}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via3_2}]}
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3040430 1714580
set v [$b findVia {via3_2}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via3_2}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3036010 1714580
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3032590 1676500
set v [$b findVia {via3_2}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via3_2}]}
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 2784190 1320140
set v [$b findVia {via7_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via7_0}]}
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2790110 1324820
set v [$b findVia {via3_2}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via3_2}]}
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 2790110 1322860
set v [$b findVia {via4_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via4_0}]}
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 2790110 1322860
set v [$b findVia {via5_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via5_0}]}
$e newPath [$tech findLayer metal6] ROUTED
$e addPoint 2790110 1320140
set v [$b findVia {via6_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via6_0}]}
$e newPath [$tech findLayer metal8] ROUTED
$e addPoint 2784190 1350540
set v [$b findVia {via8_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via8_0}]}
$e newPath [$tech findLayer metal1] ROUTED
$e addPoint 2812190 1309140
set v [$b findVia {via1_4}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via1_4}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2812190 1324820
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal1] ROUTED
$e addPoint 2820930 1320340
set v [$b findVia {via1_4}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via1_4}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2820930 1322020
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2812190 1322020
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal1] ROUTED
$e addPoint 3037530 1731100
set v [$b findVia {via1_4}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via1_4}]}
$e newPath [$tech findLayer metal8] ROUTED
$e addPoint 2801790 1353740
set v [$b findVia {via8_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via8_0}]}
$e newPath [$tech findLayer metal8] ROUTED
$e addPoint 2801790 1360140
set v [$b findVia {via8_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via8_0}]}
$e newPath [$tech findLayer metal8] ROUTED
$e addPoint 2816190 1366540
set v [$b findVia {via8_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via8_0}]}
$e end
odb::delete_dbWireEncoder $e
set target [$b findNet {services.engine\[0\].element.e32.aperture_data\[68\]}]
if {$target eq "NULL"} {error "missing target net"}
odb::dbWire_destroy [$target getWire]
set w [odb::dbWire_create $target]
set e [odb::new_dbWireEncoder]
$e begin $w
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 3581390 1425000
$e addPoint 3581950 1425000
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 3581950 1425000
$e addPoint 3581950 1464900
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 3581390 1464900
$e addPoint 3581950 1464900
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 3581950 1624500
$e addPoint 3582510 1624500
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2772290 1286180
$e addPoint 2773050 1286180
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2773050 1268260
$e addPoint 2773050 1286180
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2773050 1268260
$e addPoint 2773310 1268260
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 2773310 1252860
$e addPoint 2773310 1268260
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2773050 1252860
$e addPoint 2773310 1252860
$e newPath [$tech findLayer metal6] ROUTED
$e addPoint 3582510 1755740
$e addPoint 3582510 1760140
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 3582510 1760140
$e addPoint 3582590 1760140
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 3582510 1624500
$e addPoint 3582510 1755740
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2773050 1246980
$e addPoint 2782170 1246980
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2782170 1246140
$e addPoint 2782170 1246980
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2773050 1246980
$e addPoint 2773050 1252860
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2773050 1305780
$e addPoint 2773050 1306060
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2772290 1305780
$e addPoint 2773050 1305780
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2773430 1306060
$e addPoint 2773430 1309140
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2773050 1306060
$e addPoint 2773430 1306060
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2772290 1286180
$e addPoint 2772290 1305780
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3005610 1245020
$e addPoint 3005610 1245300
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3246510 1302140
$e addPoint 3246510 1302420
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3328610 1301860
$e addPoint 3328610 1302420
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3328610 1302420
$e addPoint 3346850 1302420
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3346850 1302420
$e addPoint 3346850 1302980
$e newPath [$tech findLayer metal6] ROUTED
$e addPoint 3482830 1304140
$e addPoint 3482830 1307340
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 3564990 1304140
$e addPoint 3564990 1305740
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 3564990 1305740
$e addPoint 3580830 1305740
$e newPath [$tech findLayer metal6] ROUTED
$e addPoint 3580830 1305740
$e addPoint 3580830 1306060
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 3580830 1374380
$e addPoint 3581390 1374380
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 3580830 1306060
$e addPoint 3580830 1374380
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 3581390 1374380
$e addPoint 3581390 1425000
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 3581950 1567500
$e addPoint 3581950 1624500
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 3581390 1567500
$e addPoint 3581950 1567500
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 3581390 1464900
$e addPoint 3581390 1567500
$e newPath [$tech findLayer metal9] ROUTED
$e addPoint 3582590 1760140
$e addPoint 4036990 1760140
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2832330 1245020
$e addPoint 2832330 1246140
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2782170 1246140
$e addPoint 2832330 1246140
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2832330 1245020
$e addPoint 2884200 1245020
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2884200 1243900
$e addPoint 2884200 1245020
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2964190 1243900
$e addPoint 2964190 1245020
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2884200 1243900
$e addPoint 2964190 1243900
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2964190 1245020
$e addPoint 3005610 1245020
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3005610 1245300
$e addPoint 3043800 1245300
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3043800 1245300
$e addPoint 3043800 1245860
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 3126110 1245300
$e addPoint 3126110 1248940
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 3126110 1299900
$e addPoint 3126110 1300460
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3126110 1300460
$e addPoint 3132150 1300460
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3132150 1299900
$e addPoint 3132150 1300460
$e newPath [$tech findLayer metal6] ROUTED
$e addPoint 3126110 1248940
$e addPoint 3126110 1299900
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3204350 1302140
$e addPoint 3204350 1303540
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3204350 1302140
$e addPoint 3227150 1302140
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3227150 1302140
$e addPoint 3227150 1302420
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3227150 1302420
$e addPoint 3229430 1302420
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3229430 1302140
$e addPoint 3229430 1302420
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3229430 1302140
$e addPoint 3246510 1302140
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3283390 1301860
$e addPoint 3283390 1302420
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3246510 1302420
$e addPoint 3283390 1302420
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3283390 1301860
$e addPoint 3328610 1301860
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3402900 1302980
$e addPoint 3402900 1303540
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3346850 1302980
$e addPoint 3402900 1302980
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3455150 1303540
$e addPoint 3455150 1303820
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3455150 1303820
$e addPoint 3461550 1303820
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3461550 1303820
$e addPoint 3461550 1304380
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3461550 1304380
$e addPoint 3466030 1304380
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 3466030 1304380
$e addPoint 3466030 1305500
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 3466030 1305500
$e addPoint 3471070 1305500
$e newPath [$tech findLayer metal6] ROUTED
$e addPoint 3471070 1304140
$e addPoint 3471070 1305500
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3402900 1303540
$e addPoint 3455150 1303540
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 3471070 1304140
$e addPoint 3482830 1304140
$e newPath [$tech findLayer metal6] ROUTED
$e addPoint 3540510 1307340
$e addPoint 3541630 1307340
$e newPath [$tech findLayer metal6] ROUTED
$e addPoint 3541630 1304140
$e addPoint 3541630 1307340
$e newPath [$tech findLayer metal6] ROUTED
$e addPoint 3541630 1304140
$e addPoint 3542750 1304140
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 3482830 1307340
$e addPoint 3540510 1307340
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 3542750 1304140
$e addPoint 3564990 1304140
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3171290 1299620
$e addPoint 3171290 1299900
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3171290 1299620
$e addPoint 3174270 1299620
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3174270 1299620
$e addPoint 3174270 1299900
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3174270 1299900
$e addPoint 3187630 1299900
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3187630 1299900
$e addPoint 3187630 1303540
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3132150 1299900
$e addPoint 3171290 1299900
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3187630 1303540
$e addPoint 3204350 1303540
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3092250 1245860
$e addPoint 3092250 1246140
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3092250 1246140
$e addPoint 3093010 1246140
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3093010 1245300
$e addPoint 3093010 1246140
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3043800 1245860
$e addPoint 3092250 1245860
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3093010 1245300
$e addPoint 3126110 1245300
$e newPath [$tech findLayer metal8] ROUTED
$e addPoint 4027390 1692940
$e addPoint 4032190 1692940
$e newPath [$tech findLayer metal8] ROUTED
$e addPoint 4027390 1683340
$e addPoint 4027390 1692940
$e newPath [$tech findLayer metal8] ROUTED
$e addPoint 4027390 1683340
$e addPoint 4028990 1683340
$e newPath [$tech findLayer metal8] ROUTED
$e addPoint 4028990 1670540
$e addPoint 4028990 1683340
$e newPath [$tech findLayer metal8] ROUTED
$e addPoint 4028990 1670540
$e addPoint 4032190 1670540
$e newPath [$tech findLayer metal9] ROUTED
$e addPoint 4032190 1670540
$e addPoint 4048190 1670540
$e newPath [$tech findLayer metal9] ROUTED
$e addPoint 4048190 1667340
$e addPoint 4048190 1670540
$e newPath [$tech findLayer metal8] ROUTED
$e addPoint 4032190 1692940
$e addPoint 4032190 1704300
$e newPath [$tech findLayer metal8] ROUTED
$e addPoint 4028990 1704300
$e addPoint 4032190 1704300
$e newPath [$tech findLayer metal8] ROUTED
$e addPoint 4028990 1704300
$e addPoint 4028990 1740940
$e newPath [$tech findLayer metal9] ROUTED
$e addPoint 4028990 1740940
$e addPoint 4036990 1740940
$e newPath [$tech findLayer metal8] ROUTED
$e addPoint 4036990 1740940
$e addPoint 4036990 1760140
$e newPath [$tech findLayer metal9] ROUTED
$e addPoint 4051390 1660940
$e addPoint 4052990 1660940
$e newPath [$tech findLayer metal9] ROUTED
$e addPoint 4048190 1667340
$e addPoint 4052990 1667340
$e newPath [$tech findLayer metal9] ROUTED
$e addPoint 4052990 1660940
$e addPoint 4052990 1667340
$e newPath [$tech findLayer metal10] ROUTED
$e addPoint 4056190 1660940
$e addPoint 4056190 1662540
$e newPath [$tech findLayer metal10] ROUTED
$e addPoint 4056190 1662540
$e addPoint 4060990 1662540
$e newPath [$tech findLayer metal10] ROUTED
$e addPoint 4060990 1662540
$e addPoint 4060990 1664140
$e newPath [$tech findLayer metal10] ROUTED
$e addPoint 4059390 1664140 0
$e addPoint 4060990 1664140
$e newPath [$tech findLayer metal10] ROUTED
$e addPoint 4051390 1660940
$e addPoint 4056190 1660940
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2773050 1268260
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2773310 1268260
set v [$b findVia {via3_2}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via3_2}]}
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2773310 1252860
set v [$b findVia {via3_2}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via3_2}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2773050 1252860
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 3582510 1755740
set v [$b findVia {via4_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via4_0}]}
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 3582510 1755740
set v [$b findVia {via5_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via5_0}]}
$e newPath [$tech findLayer metal6] ROUTED
$e addPoint 3582510 1760140
set v [$b findVia {via6_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via6_0}]}
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 3582590 1760140
set v [$b findVia {via7_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via7_0}]}
$e newPath [$tech findLayer metal8] ROUTED
$e addPoint 3582590 1760140
set v [$b findVia {via8_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via8_0}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2773050 1246980
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2782170 1246980
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2782170 1246140
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal1] ROUTED
$e addPoint 2773050 1306060
set v [$b findVia {via1_4}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via1_4}]}
$e newPath [$tech findLayer metal1] ROUTED
$e addPoint 2773430 1309140
set v [$b findVia {via1_4}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via1_4}]}
$e newPath [$tech findLayer metal6] ROUTED
$e addPoint 3482830 1304140
set v [$b findVia {via6_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via6_0}]}
$e newPath [$tech findLayer metal6] ROUTED
$e addPoint 3482830 1307340
set v [$b findVia {via6_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via6_0}]}
$e newPath [$tech findLayer metal6] ROUTED
$e addPoint 3580830 1305740
set v [$b findVia {via6_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via6_0}]}
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 3580830 1306060
set v [$b findVia {via4_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via4_0}]}
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 3580830 1306060
set v [$b findVia {via5_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via5_0}]}
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 3126110 1248940
set v [$b findVia {via4_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via4_0}]}
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 3126110 1248940
set v [$b findVia {via5_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via5_0}]}
$e newPath [$tech findLayer metal8] ROUTED
$e addPoint 4036990 1760140
set v [$b findVia {via8_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via8_0}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2832330 1246140
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2832330 1245020
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2964190 1243900
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2964190 1245020
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3126110 1245300
set v [$b findVia {via3_2}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via3_2}]}
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 3126110 1299900
set v [$b findVia {via4_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via4_0}]}
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 3126110 1299900
set v [$b findVia {via5_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via5_0}]}
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3126110 1300460
set v [$b findVia {via3_2}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via3_2}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3132150 1300460
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3132150 1299900
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3204350 1303540
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3204350 1302140
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3227150 1302140
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3229430 1302140
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3466030 1304380
set v [$b findVia {via3_2}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via3_2}]}
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 3466030 1305500
set v [$b findVia {via4_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via4_0}]}
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 3471070 1305500
set v [$b findVia {via5_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via5_0}]}
$e newPath [$tech findLayer metal6] ROUTED
$e addPoint 3471070 1304140
set v [$b findVia {via6_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via6_0}]}
$e newPath [$tech findLayer metal6] ROUTED
$e addPoint 3540510 1307340
set v [$b findVia {via6_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via6_0}]}
$e newPath [$tech findLayer metal6] ROUTED
$e addPoint 3542750 1304140
set v [$b findVia {via6_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via6_0}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3187630 1299900
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3187630 1303540
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3092250 1245860
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3093010 1245300
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal9] ROUTED
$e addPoint 4051390 1660940
set v [$b findVia {via9_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via9_0}]}
$e newPath [$tech findLayer metal8] ROUTED
$e addPoint 4032190 1670540
set v [$b findVia {via8_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via8_0}]}
$e newPath [$tech findLayer metal8] ROUTED
$e addPoint 4028990 1740940
set v [$b findVia {via8_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via8_0}]}
$e newPath [$tech findLayer metal8] ROUTED
$e addPoint 4036990 1740940
set v [$b findVia {via8_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via8_0}]}
$e end
odb::delete_dbWireEncoder $e
set target [$b findNet {services.engine\[0\].element.arithmetic.out_data\[62\]}]
if {$target eq "NULL"} {error "missing target net"}
odb::dbWire_destroy [$target getWire]
set w [odb::dbWire_create $target]
set e [odb::new_dbWireEncoder]
$e begin $w
$e newPath [$tech findLayer metal8] ROUTED
$e addPoint 2931390 1817740
$e addPoint 2931390 1819340
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3006370 1671460
$e addPoint 3007130 1671460
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3007130 1671460
$e addPoint 3007130 1673420
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3006750 1673420
$e addPoint 3007130 1673420
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3005230 1764140
$e addPoint 3005610 1764140
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3005610 1761340
$e addPoint 3005610 1764140
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3005610 1761340
$e addPoint 3007510 1761340
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3007510 1756580
$e addPoint 3007510 1761340
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3006750 1756580
$e addPoint 3007510 1756580
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3006750 1747060
$e addPoint 3006750 1756580
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3006370 1747060
$e addPoint 3006750 1747060
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3006370 1745380
$e addPoint 3006370 1747060
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3005990 1745380
$e addPoint 3006370 1745380
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3005990 1742300
$e addPoint 3005990 1745380
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3005610 1742300
$e addPoint 3005990 1742300
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3005610 1736140
$e addPoint 3005610 1742300
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3005610 1736140
$e addPoint 3005990 1736140
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3005990 1735020
$e addPoint 3005990 1736140
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3005990 1735020
$e addPoint 3006370 1735020
$e newPath [$tech findLayer metal6] ROUTED
$e addPoint 3004030 1819020
$e addPoint 3004030 1819340
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 3004030 1819020
$e addPoint 3005710 1819020
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3005710 1819020
$e addPoint 3005990 1819020
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3004090 1642340
$e addPoint 3006370 1642340
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3004090 1639540
$e addPoint 3004090 1642340
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3006370 1642340
$e addPoint 3006370 1671460
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3006370 1727100
$e addPoint 3006370 1735020
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3006750 1673420
$e addPoint 3006750 1687200
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3006370 1727100
$e addPoint 3006750 1727100
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3006750 1698620
$e addPoint 3006750 1727100
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3006750 1698620
$e addPoint 3007130 1698620
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3007130 1687200
$e addPoint 3007130 1698620
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3006750 1687200
$e addPoint 3007130 1687200
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3005990 1806900
$e addPoint 3005990 1819020
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3004850 1772820
$e addPoint 3005230 1772820
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3004850 1772820
$e addPoint 3004850 1774220
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3004850 1774220
$e addPoint 3005230 1774220
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3005230 1774220
$e addPoint 3005230 1778420
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3004850 1778420
$e addPoint 3005230 1778420
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3004850 1778420
$e addPoint 3004850 1782620
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3004850 1782620
$e addPoint 3006750 1782620
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3006750 1782620
$e addPoint 3006750 1806900
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3005990 1806900
$e addPoint 3006750 1806900
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3005230 1764140
$e addPoint 3005230 1772820
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 2764500 1820940
$e addPoint 2764500 1822540
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 2748990 1822540
$e addPoint 2764500 1822540
$e newPath [$tech findLayer metal8] ROUTED
$e addPoint 2748990 1820940
$e addPoint 2748990 1822540
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 2764500 1820940
$e addPoint 2884200 1820940
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 2884200 1819340
$e addPoint 2884200 1820940
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 2884200 1819340
$e addPoint 2931390 1819340
$e newPath [$tech findLayer metal8] ROUTED
$e addPoint 2977790 1817740
$e addPoint 2977790 1819340
$e newPath [$tech findLayer metal9] ROUTED
$e addPoint 2931390 1817740
$e addPoint 2977790 1817740
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 2977790 1819340
$e addPoint 3004030 1819340
$e newPath [$tech findLayer metal8] ROUTED
$e addPoint 2748990 1824140
$e addPoint 2748990 1846540
$e newPath [$tech findLayer metal9] ROUTED
$e addPoint 2748990 1846540
$e addPoint 2752190 1846540
$e newPath [$tech findLayer metal10] ROUTED
$e addPoint 2752190 1840140 0
$e addPoint 2752190 1846540
$e newPath [$tech findLayer metal10] ROUTED
$e addPoint 2748990 1820940
$e addPoint 2748990 1824340
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 2931390 1819340
set v [$b findVia {via7_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via7_0}]}
$e newPath [$tech findLayer metal8] ROUTED
$e addPoint 2931390 1817740
set v [$b findVia {via8_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via8_0}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3006370 1671460
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3007130 1671460
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3005610 1761340
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3007510 1761340
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3007510 1756580
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3006750 1756580
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal6] ROUTED
$e addPoint 3004030 1819340
set v [$b findVia {via6_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via6_0}]}
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 3004030 1819020
set v [$b findVia {via5_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via5_0}]}
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 3005710 1819020
set v [$b findVia {via3_2}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via3_2}]}
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 3005710 1819020
set v [$b findVia {via4_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via4_0}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3005990 1819020
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3006370 1642340
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3004090 1642340
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal1] ROUTED
$e addPoint 3004090 1639540
set v [$b findVia {via1_4}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via1_4}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3004850 1782620
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 3006750 1782620
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 2748990 1822540
set v [$b findVia {via7_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via7_0}]}
$e newPath [$tech findLayer metal8] ROUTED
$e addPoint 2748990 1820940
set v [$b findVia {via8_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via8_0}]}
$e newPath [$tech findLayer metal9] ROUTED
$e addPoint 2748990 1820940
set v [$b findVia {via9_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via9_0}]}
$e newPath [$tech findLayer metal8] ROUTED
$e addPoint 2977790 1817740
set v [$b findVia {via8_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via8_0}]}
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 2977790 1819340
set v [$b findVia {via7_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via7_0}]}
$e newPath [$tech findLayer metal8] ROUTED
$e addPoint 2748990 1824140
set v [$b findVia {via8_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via8_0}]}
$e newPath [$tech findLayer metal9] ROUTED
$e addPoint 2748990 1824340
set v [$b findVia {via9_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via9_0}]}
$e newPath [$tech findLayer metal9] ROUTED
$e addPoint 2748990 1824140
$e addPoint 2748990 1824340
$e newPath [$tech findLayer metal8] ROUTED
$e addPoint 2748990 1846540
set v [$b findVia {via8_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via8_0}]}
$e newPath [$tech findLayer metal9] ROUTED
$e addPoint 2752190 1846540
set v [$b findVia {via9_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via9_0}]}
$e end
odb::delete_dbWireEncoder $e
