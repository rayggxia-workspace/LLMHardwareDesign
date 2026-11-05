set_thread_count 16
read_db {/public/home/yuzelu/PingyangHuang/issue177-s-p4setup-20261104T054519Z/sealed/p4/flow/results/nangate45/bv1_local_s_p4/base/6_final.odb}
write_def before.def
drt::check_drc_cmd native-whole-drc.rpt 0 0 0 0 local_s_native
write_def after.def
