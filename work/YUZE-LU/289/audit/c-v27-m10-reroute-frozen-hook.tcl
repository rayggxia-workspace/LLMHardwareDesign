set b [ord::get_db_block]
set tech [[ord::get_db] getTech]
set target [$b findNet {dma_s_rsp_data\[71\]}]
if {$target eq "NULL"} {error "missing target net"}
odb::dbWire_destroy [$target getWire]
set w [odb::dbWire_create $target]
set e [odb::new_dbWireEncoder]
$e begin $w
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2053150 83580
$e addPoint 2053150 83860
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 1586310 81060
$e addPoint 1605310 81060
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 1605310 81060
$e addPoint 1605310 84140
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 1682070 84140
$e addPoint 1682070 84980
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 1728100 82740
$e addPoint 1728100 83300
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 1728100 83300
$e addPoint 1753130 83300
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 1753130 83020
$e addPoint 1753130 83300
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 1887950 83300
$e addPoint 1887950 83580
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2150590 83580
$e addPoint 2150590 83860
$e newPath [$tech findLayer metal9] ROUTED
$e addPoint 2134590 771340
$e addPoint 2156990 771340
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 2227310 956060
$e addPoint 2228430 956060
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 2228430 956060
$e addPoint 2228430 959420
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 2223390 959420
$e addPoint 2228430 959420
$e newPath [$tech findLayer metal6] ROUTED
$e addPoint 2223390 959420
$e addPoint 2223390 963900
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 2223390 963900
$e addPoint 2224510 963900
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 1586310 108220
$e addPoint 1586690 108220
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 1586690 108220
$e addPoint 1586690 114940
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 1586690 114940
$e addPoint 1588970 114940
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 1588970 114940
$e addPoint 1588970 119420
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 1588970 119420
$e addPoint 1590110 119420
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 1586310 81060
$e addPoint 1586310 108220
$e newPath [$tech findLayer metal9] ROUTED
$e addPoint 2156990 768140
$e addPoint 2156990 771340
$e newPath [$tech findLayer metal8] ROUTED
$e addPoint 2134590 771340
$e addPoint 2134590 824140
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2213690 355180
$e addPoint 2213690 355460
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2213690 355180
$e addPoint 2223390 355180
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 2223390 355180
$e addPoint 2226750 355180
$e newPath [$tech findLayer metal6] ROUTED
$e addPoint 2226750 355180
$e addPoint 2226750 355340
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 2217790 355340
$e addPoint 2226750 355340
$e newPath [$tech findLayer metal9] ROUTED
$e addPoint 2217790 355340
$e addPoint 2227390 355340
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2220150 997220
$e addPoint 2224510 997220
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 2224510 963900
$e addPoint 2224510 997220
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 1693090 81900
$e addPoint 1693090 84140
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 1693090 81900
$e addPoint 1704870 81900
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 1704870 81900
$e addPoint 1704870 82740
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 1682070 84140
$e addPoint 1693090 84140
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 1704870 82740
$e addPoint 1728100 82740
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2046300 83580
$e addPoint 2053150 83580
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2046300 83580
$e addPoint 2046300 83860
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2053150 83860
$e addPoint 2150590 83860
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2150590 83580
$e addPoint 2182510 83580
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 2176910 216860
$e addPoint 2177470 216860
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 2192190 537740
$e addPoint 2193150 537740
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 2193150 537740
$e addPoint 2196510 537740
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2204910 1096900
$e addPoint 2205710 1096900
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2205710 1096900
$e addPoint 2205710 1105020
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2205710 1105020
$e addPoint 2206090 1105020
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 2176910 109340
$e addPoint 2183070 109340
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 2183070 105420
$e addPoint 2183070 109340
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 2182510 105420
$e addPoint 2183070 105420
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 2182510 83580
$e addPoint 2182510 105420
$e newPath [$tech findLayer metal6] ROUTED
$e addPoint 2176910 109340
$e addPoint 2176910 216860
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2178350 354060
$e addPoint 2178350 355460
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2178350 355460
$e addPoint 2213690 355460
$e newPath [$tech findLayer metal6] ROUTED
$e addPoint 2195950 522620
$e addPoint 2196510 522620
$e newPath [$tech findLayer metal6] ROUTED
$e addPoint 2195950 505820
$e addPoint 2195950 522620
$e newPath [$tech findLayer metal6] ROUTED
$e addPoint 2195390 505820
$e addPoint 2195950 505820
$e newPath [$tech findLayer metal6] ROUTED
$e addPoint 2195390 494060
$e addPoint 2195390 505820
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 2195390 494060
$e addPoint 2196510 494060
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2196210 494060
$e addPoint 2196510 494060
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2196210 494060
$e addPoint 2196210 495180
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2196210 495180
$e addPoint 2196210 495740
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2196210 495740
$e addPoint 2200390 495740
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2200390 495460
$e addPoint 2200390 495740
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2200390 495460
$e addPoint 2205900 495460
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2205900 495180
$e addPoint 2205900 495460
$e newPath [$tech findLayer metal6] ROUTED
$e addPoint 2196510 522620
$e addPoint 2196510 537740
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 2180270 673820
$e addPoint 2193150 673820
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 2193150 673260
$e addPoint 2193150 673820
$e newPath [$tech findLayer metal6] ROUTED
$e addPoint 2193150 654540
$e addPoint 2193150 673260
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 2192190 654540
$e addPoint 2193150 654540
$e newPath [$tech findLayer metal8] ROUTED
$e addPoint 2192190 537740
$e addPoint 2192190 654540
$e newPath [$tech findLayer metal9] ROUTED
$e addPoint 2166590 764940
$e addPoint 2166590 768140
$e newPath [$tech findLayer metal9] ROUTED
$e addPoint 2166590 764940
$e addPoint 2174590 764940
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 2174590 764940
$e addPoint 2180830 764940
$e newPath [$tech findLayer metal6] ROUTED
$e addPoint 2180830 763980
$e addPoint 2180830 764940
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 2180270 763980
$e addPoint 2180830 763980
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 2180270 739900
$e addPoint 2180270 763980
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 2180270 739900
$e addPoint 2180830 739900
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 2180830 730940
$e addPoint 2180830 739900
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 2180270 730940
$e addPoint 2180830 730940
$e newPath [$tech findLayer metal9] ROUTED
$e addPoint 2156990 768140
$e addPoint 2166590 768140
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 2180270 673820
$e addPoint 2180270 730940
$e newPath [$tech findLayer metal6] ROUTED
$e addPoint 2177470 824140
$e addPoint 2177470 824460
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 2177470 824460
$e addPoint 2180270 824460
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 2134590 824140
$e addPoint 2177470 824140
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2196590 1080380
$e addPoint 2204910 1080380
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2196590 1078980
$e addPoint 2196590 1080380
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2196590 1078980
$e addPoint 2196970 1078980
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2196970 1078140
$e addPoint 2196970 1078980
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2195070 1078140
$e addPoint 2196970 1078140
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2195070 1077860
$e addPoint 2195070 1078140
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2194310 1063580
$e addPoint 2194310 1064980
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 2204910 1080380
$e addPoint 2204910 1096900
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 1756910 82740
$e addPoint 1756910 83020
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 1756910 82740
$e addPoint 1767570 82740
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 1767570 82740
$e addPoint 1767570 83580
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 1767570 83580
$e addPoint 1776690 83580
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 1776690 83020
$e addPoint 1776690 83580
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 1753130 83020
$e addPoint 1756910 83020
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 1845090 83020
$e addPoint 1845090 84980
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 1845090 84980
$e addPoint 1848130 84980
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 1848130 83300
$e addPoint 1848130 84980
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 1776690 83020
$e addPoint 1845090 83020
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 1848130 83300
$e addPoint 1887950 83300
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 1931350 83580
$e addPoint 1931350 85540
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 1931350 85540
$e addPoint 1941230 85540
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 1941230 83860
$e addPoint 1941230 85540
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 1887950 83580
$e addPoint 1931350 83580
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 1941230 83860
$e addPoint 2046300 83860
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2177470 239540
$e addPoint 2183670 239540
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2183670 239540
$e addPoint 2183670 251020
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2183670 251020
$e addPoint 2189790 251020
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 2189790 251020
$e addPoint 2189790 275660
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2189790 275660
$e addPoint 2190890 275660
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 2177470 216860
$e addPoint 2177470 239540
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2188990 288260
$e addPoint 2190890 288260
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2188990 288260
$e addPoint 2188990 288540
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2190890 275660
$e addPoint 2190890 288260
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 1652430 82180
$e addPoint 1652430 84140
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 1652430 82180
$e addPoint 1667630 82180
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 1667630 82180
$e addPoint 1667630 84980
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 1605310 84140
$e addPoint 1652430 84140
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 1667630 84980
$e addPoint 1682070 84980
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2194690 1063020
$e addPoint 2194690 1063580
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2194690 1063020
$e addPoint 2195070 1063020
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2195070 1057140
$e addPoint 2195070 1063020
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2195070 1057140
$e addPoint 2211790 1057140
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2211790 1056300
$e addPoint 2211790 1057140
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2211790 1056300
$e addPoint 2222050 1056300
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2222050 1050140
$e addPoint 2222050 1056300
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2222050 1050140
$e addPoint 2223950 1050140
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 2223950 1047900
$e addPoint 2223950 1050140
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 2223950 1047900
$e addPoint 2224510 1047900
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2194310 1063580
$e addPoint 2194690 1063580
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2194310 1064980
$e addPoint 2195070 1064980
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2195070 1064980
$e addPoint 2195070 1077860
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2207610 1135820
$e addPoint 2220150 1135820
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2220150 1135820
$e addPoint 2220150 1139180
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2220150 1139180
$e addPoint 2223190 1139180
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2223190 1139180
$e addPoint 2223190 1143660
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2195830 1141700
$e addPoint 2195830 1143240
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2195830 1141420
$e addPoint 2195830 1141700
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2195830 1141420
$e addPoint 2196210 1141420
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2196210 1141210
$e addPoint 2196210 1141420
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2196210 1141210
$e addPoint 2196590 1141210
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2196590 1141140
$e addPoint 2196590 1141210
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2196590 1141140
$e addPoint 2198870 1141140
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2198870 1138340
$e addPoint 2198870 1141140
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2198870 1138340
$e addPoint 2201910 1138340
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2201910 1134700
$e addPoint 2201910 1138340
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2201910 1134700
$e addPoint 2207230 1134700
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2207230 1134700
$e addPoint 2207230 1135540
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2207230 1135540
$e addPoint 2207610 1135540
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2207610 1135540
$e addPoint 2207610 1135820
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2206090 1119300
$e addPoint 2206470 1119300
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2206470 1119300
$e addPoint 2206470 1123780
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2205330 1123780
$e addPoint 2206470 1123780
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2205330 1123780
$e addPoint 2205330 1127140
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2205330 1127140
$e addPoint 2206030 1127140
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2206030 1127140
$e addPoint 2206030 1128540
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2206030 1128540
$e addPoint 2206470 1128540
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2206470 1128540
$e addPoint 2206470 1134700
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2206090 1105020
$e addPoint 2206090 1119300
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 1589470 121940
$e addPoint 1590110 121940
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 1589470 121940
$e addPoint 1589470 138740
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 1588970 138740
$e addPoint 1589470 138740
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 1590110 119420
$e addPoint 1590110 121940
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2220910 1016820
$e addPoint 2220910 1017940
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2220910 1016820
$e addPoint 2221290 1016820
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2221290 1014020
$e addPoint 2221290 1016820
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2221290 1014020
$e addPoint 2225090 1014020
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2225090 1006460
$e addPoint 2225090 1014020
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2224330 1006460
$e addPoint 2225090 1006460
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2224330 1003380
$e addPoint 2224330 1006460
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2223950 1003380
$e addPoint 2224330 1003380
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2223950 998900
$e addPoint 2223950 1003380
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2220150 998900
$e addPoint 2223950 998900
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2220910 1018220
$e addPoint 2224330 1018220
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2220910 1017940
$e addPoint 2220910 1018220
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2224330 1018220
$e addPoint 2228130 1018220
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 2224510 1037260
$e addPoint 2225070 1037260
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 2225070 1018220
$e addPoint 2225070 1037260
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2220150 997220
$e addPoint 2220150 998900
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 2224510 1037260
$e addPoint 2224510 1047900
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2188990 316540
$e addPoint 2191650 316540
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2191650 316540
$e addPoint 2191650 319200
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2191650 319200
$e addPoint 2192030 319200
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2192030 319200
$e addPoint 2192030 321020
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2192030 321020
$e addPoint 2192790 321020
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2192790 321020
$e addPoint 2192790 342860
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2192030 342860
$e addPoint 2192790 342860
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 2192030 342860
$e addPoint 2192030 348740
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2192030 348740
$e addPoint 2192790 348740
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2188990 288540
$e addPoint 2188990 316540
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2192790 348740
$e addPoint 2192790 355460
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2223190 914340
$e addPoint 2223190 916300
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2223190 916300
$e addPoint 2223950 916300
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 2223950 916300
$e addPoint 2223950 929740
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 2223950 929740
$e addPoint 2225070 929740
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 2225070 929740
$e addPoint 2225070 935340
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 2225070 935340
$e addPoint 2227310 935340
$e newPath [$tech findLayer metal6] ROUTED
$e addPoint 2227310 935340
$e addPoint 2227310 956060
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2205330 909020
$e addPoint 2215590 909020
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2215590 909020
$e addPoint 2215590 910700
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2215590 910700
$e addPoint 2215590 910980
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2215590 910980
$e addPoint 2220150 910980
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2220150 910980
$e addPoint 2220150 914340
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2220150 914340
$e addPoint 2223190 914340
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2180250 870660
$e addPoint 2180270 870660
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2180250 870660
$e addPoint 2180250 878220
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2180250 878220
$e addPoint 2184050 878220
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2184050 878220
$e addPoint 2184050 883540
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2184050 883540
$e addPoint 2187090 883540
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2187090 883540
$e addPoint 2187090 883820
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2187090 883820
$e addPoint 2205330 883820
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 2180270 824460
$e addPoint 2180270 870660
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2205330 883820
$e addPoint 2205330 909020
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2221150 495180
$e addPoint 2221150 495460
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2221150 495460
$e addPoint 2230030 495460
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2230030 495460
$e addPoint 2230030 496020
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2230030 496020
$e addPoint 2250550 496020
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2250550 493780
$e addPoint 2250550 496020
$e newPath [$tech findLayer metal9] ROUTED
$e addPoint 2220990 480140
$e addPoint 2227390 480140
$e newPath [$tech findLayer metal8] ROUTED
$e addPoint 2220990 480140
$e addPoint 2220990 481740
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 2220990 481740
$e addPoint 2226750 481740
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 2226750 481740
$e addPoint 2226750 495460
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2205900 495180
$e addPoint 2221150 495180
$e newPath [$tech findLayer metal10] ROUTED
$e addPoint 2227390 355340
$e addPoint 2227390 480140
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2271830 491820
$e addPoint 2271830 492100
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2271830 492100
$e addPoint 2274910 492100
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 2274910 492100
$e addPoint 2274910 492940
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 2274910 492940
$e addPoint 2276590 492940
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 2276590 492940
$e addPoint 2296190 492940
$e newPath [$tech findLayer metal8] ROUTED
$e addPoint 2296190 492940
$e addPoint 2296190 512140
$e newPath [$tech findLayer metal9] ROUTED
$e addPoint 2296190 512140
$e addPoint 2307390 512140
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2266890 492940
$e addPoint 2266890 493780
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2266890 492940
$e addPoint 2271830 492940
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2271830 492100
$e addPoint 2271830 492940
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2250550 493780
$e addPoint 2266890 493780
$e newPath [$tech findLayer metal10] ROUTED
$e addPoint 2313790 512140 0
$e addPoint 2313790 514600
$e newPath [$tech findLayer metal10] ROUTED
$e addPoint 2307390 512140
$e addPoint 2307390 514600
$e newPath [$tech findLayer metal10] ROUTED
$e addPoint 2307390 514600
$e addPoint 2313790 514600
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 1586310 81060
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 1605310 81060
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 1605310 84140
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 1682070 84980
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 1682070 84140
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal8] ROUTED
$e addPoint 2134590 771340
set v [$b findVia {via8_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via8_0}]}
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 2227310 956060
set v [$b findVia {via5_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via5_0}]}
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 2223390 959420
set v [$b findVia {via5_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via5_0}]}
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 2223390 963900
set v [$b findVia {via5_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via5_0}]}
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 2224510 963900
set v [$b findVia {via4_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via4_0}]}
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 2134590 824140
set v [$b findVia {via7_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via7_0}]}
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2223390 355180
set v [$b findVia {via3_2}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via3_2}]}
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 2223390 355180
set v [$b findVia {via4_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via4_0}]}
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 2226750 355180
set v [$b findVia {via5_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via5_0}]}
$e newPath [$tech findLayer metal6] ROUTED
$e addPoint 2226750 355340
set v [$b findVia {via6_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via6_0}]}
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 2217790 355340
set v [$b findVia {via7_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via7_0}]}
$e newPath [$tech findLayer metal8] ROUTED
$e addPoint 2217790 355340
set v [$b findVia {via8_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via8_0}]}
$e newPath [$tech findLayer metal9] ROUTED
$e addPoint 2227390 355340
set v [$b findVia {via9_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via9_0}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2220150 997220
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2224510 997220
set v [$b findVia {via3_2}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via3_2}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 1693090 84140
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 1693090 81900
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 1704870 81900
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 1704870 82740
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2182510 83580
set v [$b findVia {via3_2}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via3_2}]}
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 2176910 216860
set v [$b findVia {via5_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via5_0}]}
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 2177470 216860
set v [$b findVia {via4_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via4_0}]}
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 2192190 537740
set v [$b findVia {via7_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via7_0}]}
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 2193150 537740
set v [$b findVia {via5_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via5_0}]}
$e newPath [$tech findLayer metal6] ROUTED
$e addPoint 2193150 537740
set v [$b findVia {via6_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via6_0}]}
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 2196510 537740
set v [$b findVia {via5_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via5_0}]}
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2204910 1096900
set v [$b findVia {via3_2}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via3_2}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2205710 1096900
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 2176910 109340
set v [$b findVia {via5_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via5_0}]}
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 2183070 109340
set v [$b findVia {via4_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via4_0}]}
$e newPath [$tech findLayer metal1] ROUTED
$e addPoint 2178350 354060
set v [$b findVia {via1_4}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via1_4}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2178350 355460
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2192790 355460
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 2195390 494060
set v [$b findVia {via5_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via5_0}]}
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2196510 494060
set v [$b findVia {via3_2}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via3_2}]}
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 2196510 494060
set v [$b findVia {via4_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via4_0}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2196210 494060
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2196210 495180
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 2180270 673820
set v [$b findVia {via4_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via4_0}]}
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 2193150 673260
set v [$b findVia {via5_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via5_0}]}
$e newPath [$tech findLayer metal6] ROUTED
$e addPoint 2193150 654540
set v [$b findVia {via6_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via6_0}]}
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 2192190 654540
set v [$b findVia {via7_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via7_0}]}
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 2174590 764940
set v [$b findVia {via7_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via7_0}]}
$e newPath [$tech findLayer metal8] ROUTED
$e addPoint 2174590 764940
set v [$b findVia {via8_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via8_0}]}
$e newPath [$tech findLayer metal6] ROUTED
$e addPoint 2180830 764940
set v [$b findVia {via6_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via6_0}]}
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 2180830 763980
set v [$b findVia {via5_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via5_0}]}
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 2180270 763980
set v [$b findVia {via4_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via4_0}]}
$e newPath [$tech findLayer metal6] ROUTED
$e addPoint 2177470 824140
set v [$b findVia {via6_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via6_0}]}
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 2177470 824460
set v [$b findVia {via5_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via5_0}]}
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 2180270 824460
set v [$b findVia {via4_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via4_0}]}
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2204910 1080380
set v [$b findVia {via3_2}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via3_2}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2196590 1080380
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2196970 1078140
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2195070 1077860
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 1767570 82740
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 1767570 83580
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 1776690 83580
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 1776690 83020
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 1845090 83020
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 1845090 84980
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 1848130 84980
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 1848130 83300
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 1931350 83580
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 1931350 85540
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 1941230 85540
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 1941230 83860
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2177470 239540
set v [$b findVia {via3_2}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via3_2}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2183670 239540
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2183670 251020
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2189790 251020
set v [$b findVia {via3_2}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via3_2}]}
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2189790 275660
set v [$b findVia {via3_2}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via3_2}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2190890 275660
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2190890 288260
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2188990 288540
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 1652430 84140
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 1652430 82180
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 1667630 82180
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 1667630 84980
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2195070 1057140
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2222050 1056300
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2222050 1050140
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2223950 1050140
set v [$b findVia {via3_2}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via3_2}]}
$e newPath [$tech findLayer metal1] ROUTED
$e addPoint 2207610 1135820
set v [$b findVia {via1_4}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via1_4}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2207610 1135820
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2220150 1135820
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2220150 1139180
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2223190 1139180
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal1] ROUTED
$e addPoint 2223190 1143660
set v [$b findVia {via1_4}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via1_4}]}
$e newPath [$tech findLayer metal1] ROUTED
$e addPoint 2195830 1143240
set v [$b findVia {via1_4}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via1_4}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2195830 1141700
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2198870 1141140
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2198870 1138340
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2201910 1138340
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2201910 1134700
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2207230 1134700
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2206470 1123780
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2205330 1123780
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2205330 1127140
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2206470 1128540
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2206470 1134700
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 1590110 121940
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 1589470 121940
set v [$b findVia {via3_2}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via3_2}]}
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 1589470 138740
set v [$b findVia {via3_2}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via3_2}]}
$e newPath [$tech findLayer metal1] ROUTED
$e addPoint 1588970 138740
set v [$b findVia {via1_4}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via1_4}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 1588970 138740
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal1] ROUTED
$e addPoint 2220910 1017940
set v [$b findVia {via1_4}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via1_4}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2221290 1014020
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2225090 1014020
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2225090 1006460
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2224330 1006460
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2223950 998900
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2220150 998900
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal1] ROUTED
$e addPoint 2224330 1018220
set v [$b findVia {via1_4}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via1_4}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2224330 1018220
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2220910 1018220
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal1] ROUTED
$e addPoint 2228130 1018220
set v [$b findVia {via1_4}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via1_4}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2228130 1018220
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2225070 1018220
set v [$b findVia {via3_2}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via3_2}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2188990 316540
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2191650 316540
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2192790 342860
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2192030 342860
set v [$b findVia {via3_2}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via3_2}]}
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2192030 348740
set v [$b findVia {via3_2}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via3_2}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2192790 348740
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2223190 914340
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2223190 916300
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2223950 916300
set v [$b findVia {via3_2}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via3_2}]}
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 2225070 935340
set v [$b findVia {via4_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via4_0}]}
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 2227310 935340
set v [$b findVia {via5_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via5_0}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2205330 909020
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2215590 909020
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2215590 910700
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2220150 910980
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2220150 914340
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2180270 870660
set v [$b findVia {via3_2}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via3_2}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2180250 870660
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2180250 878220
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2184050 878220
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2184050 883540
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2205330 883820
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2250550 496020
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2250550 493780
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal9] ROUTED
$e addPoint 2227390 480140
set v [$b findVia {via9_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via9_0}]}
$e newPath [$tech findLayer metal8] ROUTED
$e addPoint 2220990 480140
set v [$b findVia {via8_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via8_0}]}
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 2220990 481740
set v [$b findVia {via7_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via7_0}]}
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 2226750 481740
set v [$b findVia {via4_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via4_0}]}
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 2226750 481740
set v [$b findVia {via5_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via5_0}]}
$e newPath [$tech findLayer metal6] ROUTED
$e addPoint 2226750 481740
set v [$b findVia {via6_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via6_0}]}
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2226750 495460
set v [$b findVia {via3_2}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via3_2}]}
$e newPath [$tech findLayer metal1] ROUTED
$e addPoint 2271830 491820
set v [$b findVia {via1_4}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via1_4}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2271830 492100
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2274910 492100
set v [$b findVia {via3_2}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via3_2}]}
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 2274910 492940
set v [$b findVia {via4_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via4_0}]}
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 2276590 492940
set v [$b findVia {via5_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via5_0}]}
$e newPath [$tech findLayer metal6] ROUTED
$e addPoint 2276590 492940
set v [$b findVia {via6_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via6_0}]}
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 2296190 492940
set v [$b findVia {via7_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via7_0}]}
$e newPath [$tech findLayer metal8] ROUTED
$e addPoint 2296190 512140
set v [$b findVia {via8_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via8_0}]}
$e newPath [$tech findLayer metal9] ROUTED
$e addPoint 2307390 512140
set v [$b findVia {via9_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via9_0}]}
$e end
odb::delete_dbWireEncoder $e
set target [$b findNet {services.engine\[2\].a\[114\]}]
if {$target eq "NULL"} {error "missing target net"}
odb::dbWire_destroy [$target getWire]
set w [odb::dbWire_create $target]
set e [odb::new_dbWireEncoder]
$e begin $w
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 138510 2034060
$e addPoint 139070 2034060
$e newPath [$tech findLayer metal6] ROUTED
$e addPoint 139070 2033740
$e addPoint 139070 2034060
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 138130 2034060
$e addPoint 138510 2034060
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 139070 2033740
$e addPoint 368190 2033740
$e newPath [$tech findLayer metal8] ROUTED
$e addPoint 368190 2033740
$e addPoint 368190 2089740
$e newPath [$tech findLayer metal10] ROUTED
$e addPoint 369790 2094800 0
$e addPoint 371390 2094800
$e newPath [$tech findLayer metal10] ROUTED
$e addPoint 371390 2089740
$e addPoint 371390 2094800
$e newPath [$tech findLayer metal9] ROUTED
$e addPoint 368190 2089740
$e addPoint 371390 2089740
$e newPath [$tech findLayer metal8] ROUTED
$e addPoint 368190 2089740
set v [$b findVia {via8_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via8_0}]}
$e newPath [$tech findLayer metal1] ROUTED
$e addPoint 138510 2034060
set v [$b findVia {via1_4}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via1_4}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 138510 2034060
set v [$b findVia {via2_5}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 138510 2034060
set v [$b findVia {via3_2}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via3_2}]}
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 138510 2034060
set v [$b findVia {via4_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via4_0}]}
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 139070 2034060
set v [$b findVia {via5_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via5_0}]}
$e newPath [$tech findLayer metal6] ROUTED
$e addPoint 139070 2033740
set v [$b findVia {via6_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via6_0}]}
$e newPath [$tech findLayer metal1] ROUTED
$e addPoint 138130 2034060
set v [$b findVia {via1_4}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via1_4}]}
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 368190 2033740
set v [$b findVia {via7_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via7_0}]}
$e newPath [$tech findLayer metal9] ROUTED
$e addPoint 371390 2089740
set v [$b findVia {via9_0}]
if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {via9_0}]}
$e end
odb::delete_dbWireEncoder $e
