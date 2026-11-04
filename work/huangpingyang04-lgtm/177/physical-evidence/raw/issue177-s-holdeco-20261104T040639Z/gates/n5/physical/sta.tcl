set ::env(BV1_ODB) {/public/home/yuzelu/PingyangHuang/issue177-s-holdeco-20261104T040639Z/sealed/n5/flow/results/nangate45/bv1_local_s_n5/base/6_final.odb}
set ::env(BV1_SDC) {/public/home/yuzelu/PingyangHuang/issue177-s-holdeco-20261104T040639Z/sealed/n5/flow/results/nangate45/bv1_local_s_n5/base/6_final.sdc}
set ::env(BV1_SPEF) {/public/home/yuzelu/PingyangHuang/issue177-s-holdeco-20261104T040639Z/sealed/n5/flow/results/nangate45/bv1_local_s_n5/base/6_final.spef}
rename write_sdc bv1_original_write_sdc
proc write_sdc {args} {uplevel 1 [list bv1_original_write_sdc -digits 12 {*}$args]}
source {/public/home/yuzelu/PingyangHuang/issue177-s-holdeco-20261104T040639Z/source/project/experiments/block_v1/native_sta.tcl}
