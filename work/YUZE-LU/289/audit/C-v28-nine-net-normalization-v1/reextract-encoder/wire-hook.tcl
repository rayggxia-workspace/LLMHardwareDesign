namespace eval ::c_zero_normalization {
set tech [[ord::get_db] getTech]
set block [ord::get_db_block]
set target [$block findNet {net67393}]
if {$target eq "NULL" || [$target getWire] eq "NULL"} {error "Exact target net/wire missing"}
odb::dbWire_destroy [$target getWire]
set w [odb::dbWire_create $target]
set e [odb::new_dbWireEncoder]
$e begin $w
$e newPath [$tech findLayer metal10] ROUTED
$e addPoint 2406590 1903800
$e addPoint 2409790 1903800
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2542010 2014460
$e addPoint 2542010 2015580
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2717570 2013620
$e addPoint 2717570 2013900
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2717570 2013620
$e addPoint 2721230 2013620
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2721230 2013620
$e addPoint 2721230 2013900
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2721230 2013900
$e addPoint 2736570 2013900
$e newPath [$tech findLayer metal9] ROUTED
$e addPoint 2406590 2016140
$e addPoint 2408190 2016140
$e newPath [$tech findLayer metal8] ROUTED
$e addPoint 2408190 2014540
$e addPoint 2408190 2016140
$e newPath [$tech findLayer metal6] ROUTED
$e addPoint 2408190 2014540
$e addPoint 2408190 2015020
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 2408190 2015020
$e addPoint 2409870 2015020
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 2409870 2015020
$e addPoint 2409870 2015580
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2409870 2015580
$e addPoint 2435990 2015580
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2435990 2014740
$e addPoint 2435990 2015580
$e newPath [$tech findLayer metal10] ROUTED
$e addPoint 2406590 1903800
$e addPoint 2406590 2016140
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2501350 2014460
$e addPoint 2501350 2014740
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2435990 2014740
$e addPoint 2501350 2014740
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2501350 2014460
$e addPoint 2542010 2014460
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2592550 2014460
$e addPoint 2592550 2015580
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2542010 2015580
$e addPoint 2592550 2015580
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2684700 2013900
$e addPoint 2717570 2013900
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2684700 2013620
$e addPoint 2684700 2013900
$e newPath [$tech findLayer metal10] ROUTED
$e addPoint 2409790 1875300
$e addPoint 2409790 1903800
$e newPath [$tech findLayer metal10] ROUTED
$e addPoint 2406590 1836940
$e addPoint 2409790 1836940
$e newPath [$tech findLayer metal10] ROUTED
$e addPoint 2406590 1836940
$e addPoint 2406590 1875300
$e newPath [$tech findLayer metal10] ROUTED
$e addPoint 2406590 1875300
$e addPoint 2409790 1875300
$e newPath [$tech findLayer metal10] ROUTED
$e addPoint 2409790 1832140 0
$e addPoint 2409790 1836940
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2673300 2013620
$e addPoint 2684700 2013620
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 2643950 2013900
$e addPoint 2643950 2014460
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 2643950 2013900
$e addPoint 2645070 2013900
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2645070 2013900
$e addPoint 2673300 2013900
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2673300 2013620
$e addPoint 2673300 2013900
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2592550 2014460
$e addPoint 2643950 2014460
$e newPath [$tech findLayer metal1] ROUTED
$e addPoint 2736570 2013900
set via [$block findVia {via1_4}]
if {$via ne "NULL"} {$e addVia $via} else {$e addTechVia [$tech findVia {via1_4}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2736570 2013900
set via [$block findVia {via2_5}]
if {$via ne "NULL"} {$e addVia $via} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2542010 2014460
set via [$block findVia {via2_5}]
if {$via ne "NULL"} {$e addVia $via} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2542010 2015580
set via [$block findVia {via2_5}]
if {$via ne "NULL"} {$e addVia $via} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal9] ROUTED
$e addPoint 2406590 2016140
set via [$block findVia {via9_0}]
if {$via ne "NULL"} {$e addVia $via} else {$e addTechVia [$tech findVia {via9_0}]}
$e newPath [$tech findLayer metal8] ROUTED
$e addPoint 2408190 2016140
set via [$block findVia {via8_0}]
if {$via ne "NULL"} {$e addVia $via} else {$e addTechVia [$tech findVia {via8_0}]}
$e newPath [$tech findLayer metal6] ROUTED
$e addPoint 2408190 2014540
set via [$block findVia {via6_0}]
if {$via ne "NULL"} {$e addVia $via} else {$e addTechVia [$tech findVia {via6_0}]}
$e newPath [$tech findLayer metal7] ROUTED
$e addPoint 2408190 2014540
set via [$block findVia {via7_0}]
if {$via ne "NULL"} {$e addVia $via} else {$e addTechVia [$tech findVia {via7_0}]}
$e newPath [$tech findLayer metal5] ROUTED
$e addPoint 2408190 2015020
set via [$block findVia {via5_0}]
if {$via ne "NULL"} {$e addVia $via} else {$e addTechVia [$tech findVia {via5_0}]}
$e newPath [$tech findLayer metal4] ROUTED
$e addPoint 2409870 2015020
set via [$block findVia {via4_0}]
if {$via ne "NULL"} {$e addVia $via} else {$e addTechVia [$tech findVia {via4_0}]}
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2409870 2015580
set via [$block findVia {via3_2}]
if {$via ne "NULL"} {$e addVia $via} else {$e addTechVia [$tech findVia {via3_2}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2435990 2015580
set via [$block findVia {via2_5}]
if {$via ne "NULL"} {$e addVia $via} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2435990 2014740
set via [$block findVia {via2_5}]
if {$via ne "NULL"} {$e addVia $via} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2592550 2015580
set via [$block findVia {via2_5}]
if {$via ne "NULL"} {$e addVia $via} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal2] ROUTED
$e addPoint 2592550 2014460
set via [$block findVia {via2_5}]
if {$via ne "NULL"} {$e addVia $via} else {$e addTechVia [$tech findVia {via2_5}]}
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2643950 2014460
set via [$block findVia {via3_2}]
if {$via ne "NULL"} {$e addVia $via} else {$e addTechVia [$tech findVia {via3_2}]}
$e newPath [$tech findLayer metal3] ROUTED
$e addPoint 2645070 2013900
set via [$block findVia {via3_2}]
if {$via ne "NULL"} {$e addVia $via} else {$e addTechVia [$tech findVia {via3_2}]}
$e end
odb::delete_dbWireEncoder $e
}
