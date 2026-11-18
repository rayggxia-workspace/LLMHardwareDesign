set b [ord::get_db_block]
set tech [[ord::get_db] getTech]
set target [$b findNet {dma_s_rsp_data\[4\]}]
if {$target eq "NULL"} {error "missing target net"}
odb::dbWire_destroy [$target getWire]
set w [odb::dbWire_create $target]
set e [odb::new_dbWireEncoder]
$e begin $w
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2240670 1182300
$e addPoint 2240670 1182860
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2299190 1202460
$e addPoint 2299190 1202740
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2299190 1202460
$e addPoint 2304510 1202460
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2304510 1202460
$e addPoint 2304510 1202740
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2304510 1202740
$e addPoint 2308310 1202740
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2308310 1202460
$e addPoint 2308310 1202740
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2308310 1202460
$e addPoint 2310590 1202460
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2310590 1202460
$e addPoint 2310590 1204140
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2310590 1204140
$e addPoint 2319710 1204140
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 2319710 1204140
$e addPoint 2319710 1204700
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2366070 1201060
$e addPoint 2366070 1201340
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2366070 1201060
$e addPoint 2382410 1201060
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2382410 1201060
$e addPoint 2382410 1203860
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2382410 1203860
$e addPoint 2386970 1203860
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2386970 1203860
$e addPoint 2386970 1204980
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2386970 1204980
$e addPoint 2389630 1204980
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2389630 1203860
$e addPoint 2389630 1204980
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2473990 1190700
$e addPoint 2474750 1190700
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2212170 971180
$e addPoint 2212170 972020
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2212170 971180
$e addPoint 2221150 971180
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2221150 971180
$e addPoint 2221150 971460
$e newPath [$tech findLayer metal8] ROUTED
$e addPoint 2171390 854540
$e addPoint 2172990 854540
$e newPath [$tech findLayer metal8] ROUTED
$e addPoint 2171390 947340
$e addPoint 2171390 968140
$e newPath [$tech findLayer metal8] ROUTED
$e addPoint 2171390 947340
$e addPoint 2172990 947340
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2247470 1026620
$e addPoint 2247890 1026620
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2247890 1026620
$e addPoint 2247890 1033620
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2247890 1033620
$e addPoint 2249150 1033620
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2252830 1114260
$e addPoint 2253210 1114260
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2240670 1182300
$e addPoint 2245800 1182300
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2245800 1182020
$e addPoint 2245800 1182300
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 2341550 1203020
$e addPoint 2341550 1204700
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2341550 1203020
$e addPoint 2348590 1203020
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2348590 1201340
$e addPoint 2348590 1203020
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 2319710 1204700
$e addPoint 2341550 1204700
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2348590 1201340
$e addPoint 2366070 1201340
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2426110 1202740
$e addPoint 2426110 1203860
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2389630 1203860
$e addPoint 2426110 1203860
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2598630 1192660
$e addPoint 2598630 1196020
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2598630 1196020
$e addPoint 2602050 1196020
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2602050 1195740
$e addPoint 2602050 1196020
$e newPath [$tech findLayer metal8] ROUTED
$e addPoint 2171390 849300
$e addPoint 2171390 854540
$e newPath [$tech findLayer metal8] ROUTED
$e addPoint 2171390 849300
$e addPoint 2172990 849300
$e newPath [$tech findLayer metal8] ROUTED
$e addPoint 2172990 854540
$e addPoint 2172990 947340
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 2171390 969740
$e addPoint 2177470 969740
$e newPath [$tech findLayer metal6] ROUTED
$e addPoint 2177470 969500
$e addPoint 2177470 969740
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 2176910 969500
$e addPoint 2177470 969500
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 2176910 969500
$e addPoint 2176910 971180
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2176910 971180
$e addPoint 2199250 971180
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2199250 971180
$e addPoint 2199250 972020
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 2171390 968140
$e addPoint 2171390 969740
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2199250 972020
$e addPoint 2212170 972020
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2221150 971460
$e addPoint 2245800 971460
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2264230 990220
$e addPoint 2264230 991060
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2249790 991060
$e addPoint 2264230 991060
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2249790 991060
$e addPoint 2249790 996380
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2247470 996380
$e addPoint 2249790 996380
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2268030 990360
$e addPoint 2268030 991060
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2264230 991060
$e addPoint 2268030 991060
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2260810 973140
$e addPoint 2260810 989380
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2260810 989380
$e addPoint 2260810 990500
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2260810 990500
$e addPoint 2262330 990500
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2262330 990500
$e addPoint 2262330 991060
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2245800 971460
$e addPoint 2245800 972860
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2245800 972860
$e addPoint 2260810 972860
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2260810 972860
$e addPoint 2260810 973140
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 2247470 996380
$e addPoint 2247470 1026620
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2248650 1059940
$e addPoint 2249150 1059940
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2248650 1059940
$e addPoint 2248650 1063300
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2248650 1063300
$e addPoint 2249030 1063300
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2249030 1063300
$e addPoint 2249030 1065820
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2248650 1065820
$e addPoint 2249030 1065820
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2248650 1065820
$e addPoint 2248650 1078420
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2248650 1078420
$e addPoint 2253210 1078420
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 2249150 1033620
$e addPoint 2249150 1059940
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2253210 1078420
$e addPoint 2253210 1114260
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2250170 1158220
$e addPoint 2250170 1162700
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2247470 1162700
$e addPoint 2250170 1162700
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 2247470 1162700
$e addPoint 2247470 1182020
$e newPath [$tech findLayer metal8] ROUTED
$e addPoint 2172990 837900
$e addPoint 2172990 849300
$e newPath [$tech findLayer metal8] ROUTED
$e addPoint 2171390 837900
$e addPoint 2172990 837900
$e newPath [$tech findLayer metal8] ROUTED
$e addPoint 2171390 806540
$e addPoint 2171390 837900
$e newPath [$tech findLayer metal9] ROUTED
$e addPoint 2171390 806540
$e addPoint 2174590 806540
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2258150 1147020
$e addPoint 2258150 1148980
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2255870 1147020
$e addPoint 2258150 1147020
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2255870 1131900
$e addPoint 2255870 1147020
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2255490 1131900
$e addPoint 2255870 1131900
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2255490 1124900
$e addPoint 2255490 1131900
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2252830 1124900
$e addPoint 2255490 1124900
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2250170 1152620
$e addPoint 2258150 1152620
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2258150 1148980
$e addPoint 2258150 1152620
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2250170 1152620
$e addPoint 2250170 1158220
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2252830 1114260
$e addPoint 2252830 1124900
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2451190 1202740
$e addPoint 2451190 1203580
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2426110 1202740
$e addPoint 2451190 1202740
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2527950 1192660
$e addPoint 2527950 1193220
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2527950 1192660
$e addPoint 2528330 1192660
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2528330 1192660
$e addPoint 2598630 1192660
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2474750 1193220
$e addPoint 2475130 1193220
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 2472590 1201900
$e addPoint 2472590 1203580
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 2472590 1201900
$e addPoint 2474830 1201900
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 2474830 1193220
$e addPoint 2474830 1201900
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2474830 1193220
$e addPoint 2475130 1193220
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2451190 1203580
$e addPoint 2472590 1203580
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2473990 1190700
$e addPoint 2473990 1191540
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2474750 1190700
$e addPoint 2474750 1193220
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2475130 1193220
$e addPoint 2527950 1193220
$e newPath [$tech findLayer metal8] ROUTED
$e addPoint 2172990 760140
$e addPoint 2174590 760140
$e newPath [$tech findLayer metal8] ROUTED
$e addPoint 2172990 744140
$e addPoint 2172990 760140
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 2172990 744140
$e addPoint 2174110 744140
$e newPath [$tech findLayer metal6] ROUTED
$e addPoint 2174110 743820
$e addPoint 2174110 744140
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 2150590 743820
$e addPoint 2174110 743820
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2149470 743820
$e addPoint 2150590 743820
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2149470 743540
$e addPoint 2149470 743820
$e newPath [$tech findLayer metal8] ROUTED
$e addPoint 2174590 760140
$e addPoint 2174590 806540
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2271830 1182020
$e addPoint 2271830 1182300
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2271830 1182300
$e addPoint 2278670 1182300
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2278670 1182300
$e addPoint 2278670 1183420
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2278670 1183420
$e addPoint 2280570 1183420
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2280570 1183420
$e addPoint 2280570 1187340
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2280570 1187340
$e addPoint 2286670 1187340
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 2286670 1187340
$e addPoint 2286670 1187900
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 2286670 1187900
$e addPoint 2287790 1187900
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 2287790 1187900
$e addPoint 2287790 1196300
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 2287790 1196300
$e addPoint 2288350 1196300
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2288350 1196300
$e addPoint 2291590 1196300
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2291590 1196300
$e addPoint 2291590 1202740
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2245800 1182020
$e addPoint 2271830 1182020
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2291590 1202740
$e addPoint 2299190 1202740
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 2648430 1194620
$e addPoint 2648430 1195740
$e newPath [$tech findLayer metal6] ROUTED
$e addPoint 2648430 1192140
$e addPoint 2648430 1194620
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2602050 1195740
$e addPoint 2648430 1195740
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 2648430 1192140
$e addPoint 2652990 1192140
$e newPath [$tech findLayer metal10] ROUTED
$e addPoint 2652990 1160140
$e addPoint 2654590 1160140 0
$e newPath [$tech findLayer metal10] ROUTED
$e addPoint 2654190 1160140
$e addPoint 2654190 1161340
$e newPath [$tech findLayer metal10] ROUTED
$e addPoint 2652990 1160140
$e addPoint 2652990 1171340
$e newPath [$tech findLayer metal8] ROUTED
$e addPoint 2652990 1171340
$e addPoint 2652990 1192140
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2240670 1182300
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal1] ROUTED
$e addPoint 2240670 1182860
set v [$b findVia {via1_4}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via1_4}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2310590 1202460
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2310590 1204140
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2319710 1204140
set v [$b findVia {via3_2}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via3_2}]}
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 2319710 1204700
set v [$b findVia {via4_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via4_0}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2382410 1201060
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2382410 1203860
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2386970 1203860
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2386970 1204980
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2389630 1204980
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2389630 1203860
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 2171390 968140
set v [$b findVia {via7_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via7_0}]}
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2247470 1026620
set v [$b findVia {via3_2}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via3_2}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2247890 1026620
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2247890 1033620
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2249150 1033620
set v [$b findVia {via3_2}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via3_2}]}
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2247470 1182020
set v [$b findVia {via3_2}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via3_2}]}
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 2341550 1204700
set v [$b findVia {via4_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via4_0}]}
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2341550 1203020
set v [$b findVia {via3_2}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via3_2}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2348590 1203020
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2348590 1201340
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2426110 1203860
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2426110 1202740
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2598630 1192660
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2598630 1196020
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal6] ROUTED
$e addPoint 2177470 969740
set v [$b findVia {via6_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via6_0}]}
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 2177470 969500
set v [$b findVia {via5_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via5_0}]}
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 2176910 969500
set v [$b findVia {via4_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via4_0}]}
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2176910 971180
set v [$b findVia {via3_2}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via3_2}]}
$e newPath [$tech findLayer metal1] ROUTED
$e addPoint 2264230 990220
set v [$b findVia {via1_4}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via1_4}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2264230 991060
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2249790 991060
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2249790 996380
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2247470 996380
set v [$b findVia {via3_2}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via3_2}]}
$e newPath [$tech findLayer metal1] ROUTED
$e addPoint 2268030 990360
set v [$b findVia {via1_4}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via1_4}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2268030 991060
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal1] ROUTED
$e addPoint 2260810 973140
set v [$b findVia {via1_4}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via1_4}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2260810 989380
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2260810 972860
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2249150 1059940
set v [$b findVia {via3_2}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via3_2}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2248650 1059940
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2248650 1078420
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2253210 1078420
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal1] ROUTED
$e addPoint 2250170 1158220
set v [$b findVia {via1_4}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via1_4}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2250170 1162700
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2247470 1162700
set v [$b findVia {via3_2}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via3_2}]}
$e newPath [$tech findLayer metal8] ROUTED
$e addPoint 2171390 806540
set v [$b findVia {via8_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via8_0}]}
$e newPath [$tech findLayer metal8] ROUTED
$e addPoint 2174590 806540
set v [$b findVia {via8_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via8_0}]}
$e newPath [$tech findLayer metal1] ROUTED
$e addPoint 2258150 1148980
set v [$b findVia {via1_4}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via1_4}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2258150 1147020
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2255870 1147020
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2255490 1124900
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2252830 1124900
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2250170 1152620
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2258150 1152620
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2451190 1202740
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2451190 1203580
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2527950 1193220
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2528330 1192660
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal1] ROUTED
$e addPoint 2473990 1191540
set v [$b findVia {via1_4}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via1_4}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2475130 1193220
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2472590 1203580
set v [$b findVia {via3_2}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via3_2}]}
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2474830 1193220
set v [$b findVia {via3_2}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via3_2}]}
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 2172990 744140
set v [$b findVia {via7_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via7_0}]}
$e newPath [$tech findLayer metal6] ROUTED
$e addPoint 2174110 744140
set v [$b findVia {via6_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via6_0}]}
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 2174110 743820
set v [$b findVia {via5_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via5_0}]}
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2150590 743820
set v [$b findVia {via3_2}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via3_2}]}
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 2150590 743820
set v [$b findVia {via4_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via4_0}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2149470 743820
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal1] ROUTED
$e addPoint 2149470 743540
set v [$b findVia {via1_4}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via1_4}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2280570 1183420
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2280570 1187340
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2286670 1187340
set v [$b findVia {via3_2}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via3_2}]}
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2288350 1196300
set v [$b findVia {via3_2}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via3_2}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2291590 1196300
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2291590 1202740
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2648430 1195740
set v [$b findVia {via3_2}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via3_2}]}
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 2648430 1194620
set v [$b findVia {via4_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via4_0}]}
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 2648430 1194620
set v [$b findVia {via5_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via5_0}]}
$e newPath [$tech findLayer metal6] ROUTED
$e addPoint 2648430 1192140
set v [$b findVia {via6_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via6_0}]}
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 2652990 1192140
set v [$b findVia {via7_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via7_0}]}
$e newPath [$tech findLayer metal8] ROUTED
$e addPoint 2652990 1171340
set v [$b findVia {via8_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via8_0}]}
$e newPath [$tech findLayer metal9] ROUTED
$e addPoint 2652990 1171340
set v [$b findVia {via9_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via9_0}]}
$e end
odb::delete_dbWireEncoder $e
