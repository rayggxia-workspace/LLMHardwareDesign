source {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/block-v1-20261030-400/tasks/revision300-route-v/input-diodes.tcl}
set_global_routing_layer_adjustment metal4-metal10 .20
set f [open [file join $::env(RESULTS_DIR) bv1-grt-adjustment.tsv] w]
puts $f "metal4-metal10\t0.20"
puts $f "native_rules\tunchanged"
close $f
