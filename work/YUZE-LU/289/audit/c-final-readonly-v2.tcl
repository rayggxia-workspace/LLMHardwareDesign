set_thread_count 8
read_db $::env(C_FINAL_ODB)
write_verilog fresh-from-odb.v
write_def fresh-from-odb.def
check_power_grid -net VDD
check_power_grid -net VSS
drt::check_drc -output_file fresh-native.rpt
puts READONLY_EXPORT_PG_NATIVE_COMPLETED
