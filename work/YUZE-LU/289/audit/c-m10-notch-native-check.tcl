set_thread_count 8
read_db /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/C-m10-notch-v1/patched.odb
drt::check_drc -output_file /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/C-m10-notch-v1/native-full.rpt
puts NATIVE_CHECK_COMPLETE
