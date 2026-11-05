set_thread_count 16
read_db {/public/home/yuzelu/PingyangHuang/issue177-s-holdeco-20261104T040639Z/sealed/n5/flow/results/nangate45/bv1_local_s_n5/base/6_final.odb}
write_def before.def
drt::check_drc_cmd native-whole-drc.rpt 0 0 0 0 local_s_native
write_def after.def
