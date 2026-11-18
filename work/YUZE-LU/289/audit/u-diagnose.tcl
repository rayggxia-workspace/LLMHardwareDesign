set_thread_count 2
read_liberty /OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib
foreach lib $::env(U_LIBS) {read_liberty $lib}
set res $::env(U_RESULTS)
read_db $res/6_final.odb
read_sdc $res/6_final.sdc
read_spef $res/6_final.spef
set_propagated_clock [all_clocks]
report_checks -path_delay min -format full_clock_expanded -group_path_count 20 -digits 9 > hold-paths.rpt
report_checks -path_delay max -format full_clock_expanded -group_path_count 10 -digits 9 > setup-paths.rpt
set block [ord::get_db_block]
set f [open electrical-net-drivers.tsv w]
foreach name {datapath.n32/s_rsp_data[39] datapath.store/req_data[116] datapath.store/req_data[60] wire40491/Z wire40500/Z datapath.store/req_data[57] wire40492/Z datapath.n32/s_rsp_data[75] datapath.store/req_data[125]} {
 set it [$block findITerm $name]
 if {$it eq "NULL"} {error "Missing pin $name"}
 set n [$it getNet]
 puts $f "PIN\t$name\tNET\t[$n getName]"
 foreach t [$n getITerms] {
  set inst [$t getInst]
  puts $f "TERM\t[$inst getName]\t[[$inst getMaster] getName]\t[[$t getMTerm] getName]\t[[$t getMTerm] getIoType]"
 }
}
close $f
