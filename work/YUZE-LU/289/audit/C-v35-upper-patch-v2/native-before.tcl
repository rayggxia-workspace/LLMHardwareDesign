set_thread_count 8
read_db /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/runs/C-v35-unified-i8-h100-pnone/flow/results/nangate45/c-overlay-current/base/6_final.odb
drt::check_drc -output_file /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/C-v35-upper-patch-v2/native-before.rpt
check_power_grid -net VDD
check_power_grid -net VSS
puts NATIVE_PG_CHECK_COMPLETE
