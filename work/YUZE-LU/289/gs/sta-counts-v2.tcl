# Independent exact counts, run with GS_ROLE and GS_CANDIDATE in the environment.
set c $::env(GS_CANDIDATE)
read_liberty /OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib
if {$::env(GS_ROLE) eq "S"} {
 read_liberty /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-155/bank-views-011/generation/bank/s_sram_256x128_freepdk45_TT_1p1V_25C.lib
}
set_thread_count 8
read_db $c/candidate.odb
read_sdc $c/candidate.sdc
read_spef $c/candidate.spef
set_propagated_clock [all_clocks]
sta::find_timing
set f [open $c/independent-sta-counts.tsv w]
puts $f "setup\t[sta::endpoint_violation_count max]"
puts $f "hold\t[sta::endpoint_violation_count min]"
foreach kind {capacitance slew fanout} {
 puts $f "$kind\t[sta::max_${kind}_violation_count]"
 report_check_types -max_${kind} -format end -violators -digits 9 > $c/independent-${kind}-violators.rpt
}
close $f
report_worst_slack -max -digits 9 > $c/independent-setup.rpt
report_worst_slack -min -digits 9 > $c/independent-hold.rpt
report_parasitic_annotation -report_unannotated > $c/independent-annotation.rpt
check_placement -verbose
foreach net {VDD VSS} {
 if {[check_power_grid -net $net] ne "1"} {error "Incomplete $net"}
}
check_antennas -report_file $c/independent-antenna.rpt