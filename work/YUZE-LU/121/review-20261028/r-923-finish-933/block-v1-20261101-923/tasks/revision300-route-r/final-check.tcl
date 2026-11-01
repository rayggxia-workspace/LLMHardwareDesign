set_thread_count 16
read_db {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/block-v1-20261101-923/tasks/revision300-route-r/flow/results/nangate45/bv1_block_v1_r/base/6_final.odb}
write_def final-readback.def
drt::check_drc_cmd native-whole-drc.rpt 0 0 0 0 native_whole_drc
write_def checked-readback.def
