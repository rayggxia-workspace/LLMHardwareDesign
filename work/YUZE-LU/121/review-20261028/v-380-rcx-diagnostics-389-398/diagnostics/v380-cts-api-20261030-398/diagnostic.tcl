set out [open cts-api.txt w]
puts $out [info body clock_tree_synthesis]
puts $out "CTS_ORFS"
set f [open /OpenROAD-flow-scripts/flow/scripts/cts.tcl r]
puts $out [read $f]
close $f
close $out
