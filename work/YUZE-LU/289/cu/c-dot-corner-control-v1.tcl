set_thread_count 8
set root /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu
set platform /OpenROAD-flow-scripts/flow/platforms/nangate45
read_liberty $platform/lib/NangateOpenCellLibrary_typical.lib
foreach lib $::env(CU_LIBS) {read_liberty $lib}
read_db $::env(CU_SOURCE_ODB)
read_sdc $::env(CU_SOURCE_SDC)
set_propagated_clock [all_clocks]
source $platform/setRC.tcl
source $root/geometry.tcl
geometry_snapshot geometry-source.tsv
set block [ord::get_db_block]
proc net_signature {net} {
 set a {}
 foreach it [$net getITerms] {
  set i [$it getInst]
  lappend a [list [$i getName] [[$i getMaster] getName] [$i getLocation] [$i getOrient] [[$it getMTerm] getName]]
 }
 foreach b [$net getBTerms] {lappend a [list BTERM [$b getName]]}
 return [lsort $a]
}
set signatures {};set originals {};set locked {}
foreach n [$block getNets] {if {[$n getSigType] ni {POWER GROUND}} {dict set signatures [$n getName] [net_signature $n]}}
remove_fillers
foreach i [$block getInsts] {
 dict set originals [$i getName] [list [$i getLocation] [$i getPlacementStatus]]
 if {[[$i getMaster] isBlock] || [$i getPlacementStatus] in {LOCKED FIRM}} {continue}
 set box [$i getBBox]
 if {[$box xMax] < 3920000 || [$box xMin] > 4080000 || [$box yMax] < 1264000 || [$box yMin] > 1424000} {
  dict set locked [$i getName] [$i getPlacementStatus]
  $i setPlacementStatus LOCKED
 }
}
source $root/c-dot-actual-cut-guard-v1.tcl
set d [expr {int(2000*$::env(CU_DEPTH))}]
if {$::env(CU_ORIENT) eq "left"} {
 set box [list [expr {3995320-$d}] 1328000 3995320 1384000]
} elseif {$::env(CU_ORIENT) eq "bottom"} {
 set box [list 3988000 [expr {1338400-$d}] 4011600 1338400]
} else {error "Unknown corner orientation"}
set count 0
foreach i [$block getInsts] {
 if {[[$i getMaster] isBlock] || [$i getPlacementStatus] in {LOCKED FIRM}} {continue}
 set bb [$i getBBox]
 if {[$bb xMin] < [lindex $box 2] && [$bb xMax] > [lindex $box 0] && [$bb yMin] < [lindex $box 3] && [$bb yMax] > [lindex $box 1]} {incr count}
}
if {$count==0 && $d>0} {error "No movable cells in selected keepout"}
if {$d>0} {set blockage [odb::dbBlockage_create $block {*}$box]}
puts "CORNER_PLACEMENT_BLOCKAGE $box occupied_cells=$count"
if {$d>0} {detailed_placement -max_displacement {20 20}}
check_placement -verbose
foreach {name status} $locked {[$block findInst $name] setPlacementStatus $status}
set moved 0;set f [open moved-cells.tsv w]
foreach i [$block getInsts] {
 set name [$i getName]
 if {[dict exists $originals $name] && [lindex [dict get $originals $name] 0] ne [$i getLocation]} {
  incr moved
  puts $f "$name\t[lindex [dict get $originals $name] 0]\t[$i getLocation]"
 }
}
close $f
if {$moved==0 && $d>0} {error "Corner edit produced no actual cell movement"}
set f [open changed-route-nets.tsv w];set ripped 0
foreach n [$block getNets] {
 if {[$n getSigType] in {POWER GROUND}} {continue}
 set name [$n getName]
 if {[dict get $signatures $name] ne [net_signature $n]} {
  set w [$n getWire]
  if {$w ne "NULL"} {odb::dbWire_destroy $w;incr ripped;puts $f $name}
 }
}
close $f
set f [open $root/C-outputs.txt];set outputs 0
while {[gets $f p]>=0} {
 if {[string trim $p] eq ""} {continue}
 set bt [$block findBTerm $p];set drivers {}
 foreach it [[$bt getNet] getITerms] {if {[[$it getMTerm] getIoType] eq "OUTPUT"} {lappend drivers [[[$it getInst] getMaster] getName]}}
 if {$drivers ne {BUF_X8}} {error "Output driver changed: $p $drivers"}
 incr outputs
}
close $f
if {$outputs!=153} {error "Output port count changed"}
geometry_snapshot geometry-edited.tsv
exec cmp geometry-source.tsv geometry-edited.tsv
write_db corner-edited.odb
write_def corner-edited.def
write_sdc corner-edited.sdc
puts "CORNER_EDIT_PASS moved=$moved ripped=$ripped outputs=$outputs"
if {[info exists ::env(CU_EDIT_ONLY)] && $::env(CU_EDIT_ONLY) eq "1"} {exit}
set_routing_layers -signal metal2-metal10 -clock metal4-metal10
set_global_routing_layer_adjustment metal2-metal10 0.0
global_route -use_cugr -congestion_iterations 3 -verbose -congestion_report_file congestion.rpt
write_guides route.guide
write_db corner-global.odb
detailed_route -output_drc route-drc.rpt -output_maze maze.log -via_in_pin_bottom_layer metal10 -via_in_pin_top_layer metal10 -via_access_layer metal10 -droute_end_iter 5 -verbose 1 -drc_report_iter_step 5
filler_placement {FILLCELL_X32 FILLCELL_X16 FILLCELL_X8 FILLCELL_X4 FILLCELL_X2 FILLCELL_X1}
add_global_connection -net VDD -inst_pattern .* -pin_pattern VDD -power
add_global_connection -net VSS -inst_pattern .* -pin_pattern VSS -ground
global_connect
geometry_snapshot geometry-final.tsv
exec cmp geometry-source.tsv geometry-final.tsv
set res $::env(CU_RESULTS)
write_db $res/6_final.odb
write_def $res/6_final.def
write_sdc $res/6_final.sdc
write_verilog $res/6_final.v
if {[file size route-drc.rpt]!=0} {puts CORNER_BOUNDED_NATIVE_FAILED_DIAGNOSTIC_ONLY;exit 3}
extract_parasitics -ext_model_file $platform/rcx_patterns.rules
write_spef $res/6_final.spef
write_db $res/6_post_rcx.odb
write_def $res/6_post_rcx.def
puts CORNER_CANDIDATE_PENDING_FRESH_STA_PG_FULL_PHYSICAL
