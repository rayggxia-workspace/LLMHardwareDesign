read_db {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/router-fastroute24phase-preflight-172/case-0/before.odb}
set_thread_count 16
set_routing_layers -signal metal11-metal12 -clock metal11-metal12
help read_guides
read_guides {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/router-fastroute24phase-preflight-172/case-0/route.guide}
detailed_route -droute_end_iter 1 -drc_report_iter_step 1 -output_drc {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/router-bounded-snapshot-preflight-180/drc.rpt} -via_in_pin_bottom_layer metal11 -via_in_pin_top_layer metal11 -verbose 1
write_def {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/router-bounded-snapshot-preflight-180/snapshot.def}
write_db {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/router-bounded-snapshot-preflight-180/snapshot.odb}
