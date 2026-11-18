set_thread_count 8
set root /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117
set platform /OpenROAD-flow-scripts/flow/platforms/nangate45
read_liberty $platform/lib/NangateOpenCellLibrary_typical.lib
foreach lib $::env(CU_LIBS) {read_liberty $lib}
read_db $root/audit/C-static-greedy-v2/best.odb
set b [ord::get_db_block]
set src [$b findInst _280589_]
if {$src eq "NULL" || ![string match XNOR2_X* [[$src getMaster] getName]]} {error "Unexpected target"}
set sink [$src findITerm A]
set old [$sink getNet]
if {[$old getName] ne "net58124"} {error "Unexpected original net"}
set ins [odb::dbInst_create $b [[ord::get_db] findMaster BUF_X$::env(PROBE_SIZE)] i289_root_receiver]
lassign [$src getLocation] x y
$ins setLocation $x $y
$ins setPlacementStatus PLACED
set short [odb::dbNet_create $b i289_root_receiver_stub]
$sink disconnect
$sink connect $short
[$ins findITerm A] connect $old
[$ins findITerm Z] connect $short
read_sdc $root/cu/runs/C-v27-joint-e20-h30/flow/results/nangate45/c-overlay-current/base/6_final.sdc
set_propagated_clock [all_clocks]
source $platform/setRC.tcl
read_spef conditional.spef
report_checks -path_delay max -fields {slew cap input_pin net fanout} -group_path_count 10 -digits 9 > paths.rpt
report_check_types -max_capacitance -max_slew -violators -digits 9 > electrical.rpt
report_wns -digits 9
report_tns -digits 9
set f [open metrics.tsv w]
puts $f "[sta::worst_slack -max]\t[sta::worst_slack -min]"
close $f
puts CONDITIONAL_ONLY_NOT_PHYSICAL_SIGNOFF
