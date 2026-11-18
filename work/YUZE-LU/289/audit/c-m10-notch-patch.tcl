set_thread_count 8
read_db /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/runs/C-v20-native-clock4/flow/results/nangate45/c-overlay-current/base/6_final.odb
write_def /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/C-m10-notch-v1/before.def
write_verilog /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/C-m10-notch-v1/before.v
set b [ord::get_db_block]
set count 0
foreach n [$b getNets] {
 if {[string map {\\ ""} [$n getName]] eq {dma_s_rsp_data[52]}} {odb::dbWire_destroy [$n getWire];incr count}
}
if {$count != 1} {error "target not unique"}
read_def -incremental /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/C-m10-notch-v1/patch.def
write_db /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/C-m10-notch-v1/patched.odb
write_def /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/C-m10-notch-v1/patched.def
write_verilog /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/C-m10-notch-v1/patched.v
puts PATCH_WRITTEN
