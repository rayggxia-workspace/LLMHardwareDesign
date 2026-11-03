set_thread_count 16
read_db {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/r256-native-353/3530/gates/sealed/flow/results/nangate45/bv1_control_reset_distribution_r53/base/6_final.odb}
write_def before.def
if {[llength [info commands ::drt::check_drc_cmd]]!=1} {error "Missing whole-chip DRC API"}
drt::check_drc_cmd native-whole-drc.rpt 0 0 0 0 native_whole_drc
write_def after.def
