set_thread_count 16
read_db {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/block-v1-20261101-880/tasks/revision300-r-composed-vias/composed-candidate.odb}
source {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/block-v1-20261101-880/tasks/revision300-r-composed-neighborhood/region-base.tcl}
source {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/block-v1-20261101-880/src/project/experiments/block_v1/geometry_windows.tcl}
::region::add 0 645750 2467630 653850 2475770
::region::add 1 1723050 2950630 1731150 2958770
::region::add 2 592340 2453490 600480 2461560
::region::add 3 1390340 3641810 1398480 3649880
::region::add 4 1669640 317720 1677780 325790
::region::add 5 1709540 3045760 1717680 3053830
::region::add 6 2032920 3499920 2041060 3507990
::region::add 7 2232420 788960 2240560 797030
::region::add 8 2312220 1976090 2320360 1984160
::region::add 9 2392020 609970 2400160 618040
::region::add 10 2392020 788890 2400160 796960
::region::add 11 2591520 2349120 2599660 2357190
::region::add 12 2711220 4024360 2719360 4032430
::region::add 13 3145940 434760 3154080 442830
::region::add 14 3145940 3976760 3154080 3984830
::region::add 15 3185840 3107360 3193980 3115430
::region::add 16 3345440 3471640 3353580 3479710
::region::add 17 3628920 1242840 3637060 1250910
::region::add 18 3708720 1576600 3716860 1584670
::region::add 19 3744440 1298840 3752580 1306910
::region::add 20 4187520 1095210 4195660 1103280
::region::add 21 4267320 4098490 4275460 4106560
::region::add 22 4307220 3784960 4315360 3793030
::region::add 23 4546620 1963560 4554760 1971630
::region::add 24 454970 1669630 463090 1677770
::region::add 25 611140 1510030 619270 1518170
::region::add 26 1029170 2148430 1037250 2156570
::region::add 27 1360150 2232430 1368210 2240570
::region::add 28 1477190 2627230 1485250 2635370
::region::add 29 1849590 3190030 1857650 3198170
::region::add 30 1973130 3664630 1981190 3672770
::region::add 31 1988980 3469330 1997090 3477470
::region::add 32 2048730 2312230 2056810 2320370
::region::add 33 2058250 3030430 2066310 3038570
::region::add 34 2206030 2068630 2214130 2076770
::region::add 35 2414650 3265630 2422690 3273770
::region::add 36 2590970 2387830 2599090 2395970
::region::add 37 2630570 2866630 2638590 2874770
::region::add 38 2668870 2228230 2676930 2236370
::region::add 39 2696650 2387830 2704710 2395970
::region::add 40 2716810 2631430 2724850 2639570
::region::add 41 2738090 1031230 2746130 1039370
::region::add 42 2738090 3265630 2746130 3273770
::region::add 43 2796550 3110230 2804610 3118370
::region::add 44 3067930 3908230 3075970 3916370
::region::add 45 3069050 1195030 3077110 1203170
::region::add 46 3314490 2870830 3322610 2878970
::region::add 47 3422410 712030 3430510 720170
::region::add 48 3564910 1190830 3572930 1198970
::region::add 49 3794430 2711230 3802530 2719370
::region::add 50 3800970 1514230 3808990 1522370
::region::add 51 3889450 2707030 3897530 2715170
::region::add 52 4317290 3030430 4325410 3038570
::region::add 53 4349990 3748630 4358050 3756770
::region::add 54 3708720 1576599 3716800 1584601

rename bvgeom::rectangle bvgeom::original_rectangle
proc bvgeom::rectangle {stream net layer kind object {dx 0} {dy 0} {transform ""}} {
  incr ::region::scanned
  set x0 [expr {[$object xMin]+$dx}];set y0 [expr {[$object yMin]+$dy}]
  set x1 [expr {[$object xMax]+$dx}];set y1 [expr {[$object yMax]+$dy}]
  if {[present $transform]} {
    set xs {};set ys {}
    foreach x [list $x0 $x1] {foreach y [list $y0 $y1] {
      set point [odb::new_Point $x $y];$transform apply $point
      lappend xs [$point getX];lappend ys [$point getY];odb::delete_Point $point
    }}
    set x0 [tcl::mathfunc::min {*}$xs];set x1 [tcl::mathfunc::max {*}$xs]
    set y0 [tcl::mathfunc::min {*}$ys];set y1 [tcl::mathfunc::max {*}$ys]
  }
  foreach index [::region::hits $x0 $y0 $x1 $y1] {
    puts $stream "$index\t$net\t[$layer getName]\t$kind\t$x0\t$y0\t$x1\t$y1"
    dict set ::region::aliases $net 1;incr ::region::emitted
  }
}
bvgeom::export neighborhood.tsv
set block [ord::get_db_block]
set f [open neighborhood.tsv a]
foreach inst [$block getInsts] {
  set boxes [[$inst getMaster] getObstructions]
  if {[llength $boxes]==0} {continue}
  set transform [$inst getTransform]
  foreach box $boxes {bvgeom::db_box $f i[$inst getId] $box instance-obstruction $transform}
}
foreach obs [$block getObstructions] {bvgeom::db_box $f block-obstruction [$obs getBBox] block-obstruction}
close $f
set f [open net-aliases.tsv w]
foreach net [$block getNets] {set alias n[$net getId]
  if {[dict exists $::region::aliases $alias]} {puts $f "$alias\t[binary encode hex [encoding convertto utf-8 [$net getName]]]"}
}
close $f
set f [open scan-counts.tsv w];puts $f "$::region::scanned\t$::region::emitted";close $f
set tech [ord::get_db_tech]
set f [open layer-dimensions.tsv w]
foreach layer [$tech getLayers] {puts $f "[$layer getName]\t[$layer getWidth]\t[$layer getSpacing]"}
close $f
set f [open via-footprints.tsv w]
foreach via [$tech getVias] {
  foreach box [$via getBoxes] {puts $f "[$via getName]\t[[$box getTechLayer] getName]\t[$box xMin]\t[$box yMin]\t[$box xMax]\t[$box yMax]"}
}
close $f
