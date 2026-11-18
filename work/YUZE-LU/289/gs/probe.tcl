set platform /OpenROAD-flow-scripts/flow/platforms/nangate45
read_liberty $platform/lib/NangateOpenCellLibrary_typical.lib
set role $::env(GS_ROLE)
if {$role eq "G"} {
 set base /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-201-compact-ge/2ba89c0bd/release/g
} elseif {$role eq "S"} {
 read_liberty /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-155/bank-views-011/generation/bank/s_sram_256x128_freepdk45_TT_1p1V_25C.lib
 set base /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-200-compact-local-s/run08-base0/results/0/flow/results/nangate45/local_s_base/base
} else {error "unknown GS_ROLE"}
read_db $base/6_final.odb
read_sdc $base/6_final.sdc
read_spef $base/6_final.spef
set_propagated_clock [all_clocks]
set block [ord::get_db_block]
set fp [open ports.tsv w]
puts $fp "port\tdirection\tinstance\tmaster\tpin\tpin_direction\tx\ty"
foreach b [$block getBTerms] {
 set name [$b getName]
 if {($role eq "G" && ![string match {out_*} $name]) || ($role eq "S" && $name ne "req_ready")} {continue}
 foreach it [[$b getNet] getITerms] {
  set i [$it getInst];set mt [$it getMTerm];lassign [$i getLocation] x y
  puts $fp "$name\t[$b getIoType]\t[$i getName]\t[[$i getMaster] getName]\t[$mt getName]\t[$mt getIoType]\t$x\t$y"
 }
}
close $fp
report_worst_slack -max -digits 9 > setup.rpt
report_worst_slack -min -digits 9 > hold.rpt
foreach c {max_slew max_capacitance} {report_check_types -$c -format end -max_count 200 -digits 9 > $c.rpt}
puts "BUF_X8 master [[ord::get_db] findMaster BUF_X8]"
puts GS_PROBE_COMPLETE
