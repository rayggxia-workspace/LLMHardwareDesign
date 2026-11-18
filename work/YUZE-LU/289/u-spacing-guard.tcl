set root /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117
set platform /OpenROAD-flow-scripts/flow/platforms/nangate45
set source $root/cu/runs/U-v13-electrical-f50-x4/flow/results/nangate45/u-overlay-current/base
set res $::env(U_RESULTS)
set_thread_count 8
read_liberty $platform/lib/NangateOpenCellLibrary_typical.lib
foreach lib $::env(U_LIBS) {read_liberty $lib}
read_db $source/6_final.odb
read_sdc $source/6_final.sdc
set_propagated_clock [all_clocks]
set block [ord::get_db_block]
source $root/cu/geometry.tcl
geometry_snapshot geometry-before.tsv
set existing [dict create]
foreach name {local_s_base block_v2_e_compact} {
 set m [[ord::get_db] findMaster $name]
 if {$m eq "NULL"} {error "Missing original master $name"}
 foreach box [$m getObstructions] {
  dict set existing [list $name [[$box getTechLayer] getName] [$box xMin] [$box yMin] [$box xMax] [$box yMax]] 1
 }
}
set added 0
set f [open $root/u-physical/leaf-cut-obs.tsv]
while {[gets $f line]>=0} {
 lassign [split $line \t] name layer x0 y0 x1 y1
 set key [list $name $layer $x0 $y0 $x1 $y1]
 if {[dict exists $existing $key]} {continue}
 set m [[ord::get_db] findMaster $name]
 odb::dbBox_create $m [[ord::get_db_tech] findLayer $layer] $x0 $y0 $x1 $y1
 dict set existing $key 1
 incr added
}
close $f
puts "ACTUAL_CUT_OBSTRUCTIONS_ADDED $added"
if {$added==0} {error "No new cut constraints; experiment would not address missing cut geometry"}
set f [open $root/u-remove-pg-stacks.tsv]
set report [open removed-pg-stacks.tsv w]
set removed 0
while {[gets $f line]>=0} {
 lassign [split $line \t] rail x y
 set matched {};set kinds {}
 foreach sw [[$block findNet $rail] getSWires] {
  foreach box [$sw getWires] {
   if {![$box isVia] || [$box getViaXY] ne [list $x $y]} {continue}
   set via [$box getTechVia]
   if {$via eq "NULL"} {set via [$box getBlockVia]}
   set levels {}
   foreach shape [$via getBoxes] {
    set l [[$shape getTechLayer] getRoutingLevel]
    if {$l} {lappend levels $l}
   }
   set levels [lsort -integer -unique $levels]
   if {$levels ni {{7 8} {8 9} {9 10}}} {continue}
   lappend matched $box;lappend kinds $levels
   puts $report "$rail\t$x\t$y\t[$via getName]\t$levels"
  }
 }
 if {[lsort $kinds] ne {{7 8} {8 9} {9 10}}} {error "Expected exactly one complete redundant stack at $rail $x $y: $kinds"}
 foreach box $matched {odb::dbSBox_destroy $box;incr removed}
}
close $f;close $report
if {$removed!=30} {error "Unexpected removed PG shape count $removed"}
foreach rail {VDD VSS} {if {[check_power_grid -net $rail] ne "1"} {error "Disconnected $rail after exact PG stack removal"}}
remove_fillers
set reroute [dict create]
foreach inst [$block getInsts] {
 if {[[$inst getMaster] getName] ni {local_s_base block_v2_e_compact}} {continue}
 foreach it [$inst getITerms] {
  set net [$it getNet]
  if {$net ne "NULL" && [$net getSigType] ni {POWER GROUND}} {dict set reroute [$net getName] $net}
 }
}
set f [open ripped-macro-nets.tsv w]
dict for {name net} $reroute {
 set wire [$net getWire]
 if {$wire ne "NULL"} {odb::dbWire_destroy $wire}
 puts $f $name
}
close $f
puts "MACRO_NETS_RIPPED [dict size $reroute]"
write_db guarded-before-route.odb
set_routing_layers -signal metal1-metal10 -clock metal1-metal10
set_global_routing_layer_adjustment metal2-metal6 0.20
set_global_routing_layer_adjustment metal7-metal10 0.0
global_route -allow_congestion -verbose -congestion_report_file congestion.rpt
write_guides reroute.guide
detailed_route -output_drc route-drc.rpt -output_maze maze.log -via_in_pin_bottom_layer metal10 -via_in_pin_top_layer metal10 -via_access_layer metal10 -droute_end_iter 64 -verbose 1 -drc_report_iter_step 5
filler_placement {FILLCELL_X32 FILLCELL_X16 FILLCELL_X8 FILLCELL_X4 FILLCELL_X2 FILLCELL_X1}
add_global_connection -net VDD -inst_pattern .* -pin_pattern VDD -power
add_global_connection -net VSS -inst_pattern .* -pin_pattern VSS -ground
global_connect
foreach rail {VDD VSS} {if {[check_power_grid -net $rail] ne "1"} {error "Disconnected final $rail"}}
geometry_snapshot geometry-after.tsv
exec cmp geometry-before.tsv geometry-after.tsv
file copy geometry-before.tsv $res/geometry-before.tsv
write_db $res/6_final.odb
write_def $res/6_final.def
write_verilog $res/6_final.v
write_sdc $res/6_final.sdc
extract_parasitics -ext_model_file $platform/rcx_patterns.rules
write_spef $res/6_final.spef
puts "U_SPACING_GUARD_CANDIDATE_COMPLETE_NOT_ACCEPTED"
