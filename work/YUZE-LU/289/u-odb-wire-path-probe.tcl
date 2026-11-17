read_db $::env(PROBE_ODB)
set block [ord::get_db_block]
foreach name {i289_repeater_store124_net net22175 net38689 {e_out_data[26]} net38652 net38650} {
 set net [$block findNet $name]
 if {$net eq "NULL"} {error "Missing $name"}
 puts "NET $name"
 odb::dumpWirePaths4Net $net 0 0
}
