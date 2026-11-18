set_thread_count 8
set root /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu
set platform /OpenROAD-flow-scripts/flow/platforms/nangate45
read_liberty $platform/lib/NangateOpenCellLibrary_typical.lib
foreach lib $::env(CU_LIBS) {read_liberty $lib}
read_db global-candidate.odb
read_sdc route-source.sdc
set_propagated_clock [all_clocks]
source $platform/setRC.tcl
source $root/geometry.tcl
geometry_snapshot geometry-before-route.tsv
set_routing_layers -signal metal2-metal10 -clock metal$::env(CU_CLOCK_MIN)-metal10
set b [ord::get_db_block]
set inst [$b findInst services.store.leaf]
if {$inst eq "NULL"} {error "Missing diagnosed S instance"}
set targets {};set npins 0
foreach it [$inst getITerms] {
 if {[regexp {^req_data\[([0-9]+)\]$} [[$it getMTerm] getName]]} {
  incr npins
  dict set targets [[$it getNet] getName] [$it getNet]
 }
}
if {$npins!=128} {error "Expected128 S req_data ports, found $npins"}
set dotinstances 0;set dotnets {}
foreach di [$b getInsts] {
 if {[[$di getMaster] getName] ne "e_s32_pipeline_128"} {continue}
 incr dotinstances
 foreach it [$di getITerms] {
  set dn [$it getNet]
  if {$dn ne "NULL" && [$dn getSigType] ni {POWER GROUND}} {
   dict set targets [$dn getName] $dn
   dict set dotnets [$dn getName] 1
  }
 }
}
if {$dotinstances!=1 || [dict size $dotnets]==0} {error "Changed dot master net binding invalid"}
puts "CHANGED_DOT_CUT_OBS_SIGNAL_NETS [dict size $dotnets]"
set f [open repaired-macro-access-nets.tsv w]
foreach {name net} $targets {
 set w [$net getWire]
 if {$w ne "NULL"} {odb::dbWire_destroy $w;puts $f $name}
}
close $f
puts "DIAGNOSED_S_REQUEST_ACCESS_GROUP_RIPPED pins=$npins nets=[dict size $targets]"
set_global_routing_layer_adjustment metal2-metal10 0.0
global_route -use_cugr -congestion_iterations 3 -verbose -congestion_report_file access-recovery-congestion.rpt
write_guides recovered.guide
write_db recovered-global.odb
detailed_route -output_drc route-drc.rpt -output_maze maze.log -via_in_pin_bottom_layer metal10 -via_in_pin_top_layer metal10 -via_access_layer metal1 -droute_end_iter 5 -verbose 1 -drc_report_iter_step 5
filler_placement {FILLCELL_X32 FILLCELL_X16 FILLCELL_X8 FILLCELL_X4 FILLCELL_X2 FILLCELL_X1}
add_global_connection -net VDD -inst_pattern .* -pin_pattern VDD -power
add_global_connection -net VSS -inst_pattern .* -pin_pattern VSS -ground
global_connect
geometry_snapshot geometry-after-route.tsv
exec cmp geometry-before-route.tsv geometry-after-route.tsv
set res $::env(CU_RESULTS)
write_db $res/6_final.odb
write_def $res/6_final.def
write_verilog $res/6_final.v
write_sdc $res/6_final.sdc
if {[file size route-drc.rpt] != 0} {
 estimate_parasitics -placement
 report_worst_slack -max -digits 9 > diagnostic-placement-setup.rpt
 puts BOUNDED_FIVE_ITERATIONS_NATIVE_DRC_FAILED_DIAGNOSTIC_ONLY
 exit 3
}
extract_parasitics -ext_model_file $platform/rcx_patterns.rules
write_spef $res/6_final.spef
write_def $res/6_post_rcx.def
write_db $res/6_post_rcx.odb
puts NATIVE_CANDIDATE_REQUIRES_FRESH_STA_PG_AND_FULL_DECK