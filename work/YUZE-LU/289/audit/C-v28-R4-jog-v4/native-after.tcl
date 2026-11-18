set_thread_count 8
read_db /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/C-v28-R4-jog-v4/patched.odb
drt::check_drc -output_file /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/C-v28-R4-jog-v4/native-after.rpt
check_power_grid -net VDD
check_power_grid -net VSS
puts NATIVE_PG_CHECK_COMPLETE
