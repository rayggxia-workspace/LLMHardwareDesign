# Candidate implementation only; independent DRC/LEC/STA gates still required.
set platform /OpenROAD-flow-scripts/flow/platforms/nangate45
read_liberty $platform/lib/NangateOpenCellLibrary_typical.lib
set role $::env(GS_ROLE)
set mode $::env(GS_MODE)
if {$role eq "G"} {
 set base /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-201-compact-ge/2ba89c0bd/release/g
 set ports {out_valid}
 for {set i 0} {$i < 32} {incr i} {lappend ports "out_data\[$i\]"}
} else {
 read_liberty /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-155/bank-views-011/generation/bank/s_sram_256x128_freepdk45_TT_1p1V_25C.lib
 set base /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-200-compact-local-s/run08-base0/results/0/flow/results/nangate45/local_s_base/base
 set ports {req_ready}
}
set_thread_count $::env(OMP_NUM_THREADS)
read_db $base/6_final.odb
read_sdc $base/6_final.sdc
set_propagated_clock [all_clocks]
set block [ord::get_db_block]
proc boundary {} {
 set result {}
 foreach b [[ord::get_db_block] getBTerms] {
  foreach p [$b getBPins] {foreach x [$p getBoxes] {lappend result [list [$b getName] [[$x getTechLayer] getName] [$x xMin] [$x yMin] [$x xMax] [$x yMax]]}}
 }
 return [lsort $result]
}
set old_boundary [boundary]
set old_die [list [[$block getDieArea] xMin] [[$block getDieArea] yMin] [[$block getDieArea] xMax] [[$block getDieArea] yMax]]
set changes [open changes.tsv w]
puts $changes "port\tinstance\tbefore\tafter"
set targets {}
foreach p $ports {
 set b [$block findBTerm $p]
 if {$b eq "NULL" || [$b getIoType] ne "OUTPUT"} {error "missing output $p"}
 set drivers {}
 foreach it [[$b getNet] getITerms] {if {[[$it getMTerm] getIoType] eq "OUTPUT"} {lappend drivers [$it getInst]}}
 if {[llength $drivers] != 1} {error "ambiguous driver $p"}
 set i [lindex $drivers 0];set name [$i getName];set master [[$i getMaster] getName]
 if {$master ne "BUF_X4"} {error "source mismatch $p $master"}
 lappend targets $name
 puts $changes "$p\t$name\t$master\tBUF_X8"
}
remove_fillers
foreach name $targets {if {![replace_cell $name BUF_X8]} {error "Replacement failed: $name"}}
close $changes
# Remove obsolete detailed signal routes after cell geometry changes; PG special wires remain.
foreach net [$block getNets] {
 if {[$net getSigType] in {POWER GROUND}} {continue}
 set wire [$net getWire]
 if {$wire ne "NULL"} {odb::dbWire_destroy $wire}
}
set_wire_rc -signal -layer metal3
set_wire_rc -clock -layer metal5
set_routing_layers -signal metal1-metal10 -clock metal1-metal10
set_global_routing_layer_adjustment metal1-metal10 0.3
detailed_placement
check_placement -verbose
# New guide generation after final-cell resize; source database remains unchanged.
global_route -congestion_report_file congestion.rpt -verbose
estimate_parasitics -global_routing
if {$mode ne "minimal"} {
 set margin 0.03
 if {$mode eq "hold08"} {set margin 0.08}
 repair_timing -hold -hold_margin $margin
 detailed_placement
 global_route -congestion_report_file congestion-after.rpt -verbose
}
foreach name $targets {
 if {[[[$block findInst $name] getMaster] getName] ne "BUF_X8"} {error "target changed after optimization"}
}
detailed_route -output_drc route-drc.rpt -output_maze maze.log -via_in_pin_bottom_layer metal10 -via_in_pin_top_layer metal10 -droute_end_iter 64 -verbose 1 -drc_report_iter_step 5 -via_access_layer metal10
if {$role eq "S"} {
 set ::env(RESULTS_DIR) [pwd]
 source /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-200-compact-local-s/run08-base0/results/0/landing-patches.tcl
}
filler_placement {FILLCELL_X32 FILLCELL_X16 FILLCELL_X8 FILLCELL_X4 FILLCELL_X2 FILLCELL_X1}
global_connect
if {[boundary] ne $old_boundary} {error "interface geometry changed"}
set new_die [list [[$block getDieArea] xMin] [[$block getDieArea] yMin] [[$block getDieArea] xMax] [[$block getDieArea] yMax]]
if {$old_die ne $new_die} {error "die changed"}
foreach p $ports {
 set drivers {}
 foreach it [[[$block findBTerm $p] getNet] getITerms] {
  if {[[$it getMTerm] getIoType] eq "OUTPUT"} {lappend drivers [[[$it getInst] getMaster] getName]}
 }
 if {$drivers ne {BUF_X8}} {error "Final endpoint $p has wrong drivers: $drivers"}
}
write_db candidate.odb
write_def candidate.def
write_verilog candidate.v
write_sdc candidate.sdc
extract_parasitics -ext_model_file $platform/rcx_patterns.rules
write_spef candidate.spef
read_spef candidate.spef
report_worst_slack -max -digits 9 > setup.rpt
report_worst_slack -min -digits 9 > hold.rpt
foreach c {max_slew max_capacitance max_fanout} {report_check_types -$c -format end -max_count 200 -digits 9 > $c.rpt}
report_parasitic_annotation -report_unannotated > annotation.rpt
check_setup -verbose > constraints.rpt
check_power_grid -net VDD > pg-vdd.rpt
check_power_grid -net VSS > pg-vss.rpt
puts GS_CANDIDATE_COMPLETE_NOT_QUALIFIED
