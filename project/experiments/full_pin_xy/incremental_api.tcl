# Read actual installed APIs; no source DB or geometry mutation.
foreach cmd {read_guides set_nets_to_route global_route detailed_route repair_design repair_timing} {
  puts "NATIVE_API $cmd exists=[llength [info commands $cmd]]"
  if {[llength [info commands $cmd]]} {help $cmd}
}
