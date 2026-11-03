# Source inside the fixed ORFS image; no netlist needed for these help queries.
puts "TOOL [ord::openroad_version]"
help set_max_delay
help set_min_delay
help report_check_types
help find_timing_paths
help report_parasitic_annotation
help set_dont_touch
help set_placement_padding
help extract_parasitics
help get_cells
help get_pins
help all_fanin
help set_bus_skew
help report_checks
help report_worst_slack
help check_setup
set f [open source-snapshot.json r]
set manifest [read $f]
close $f
if {[regexp {"reuse": "([^"]+)"} $manifest -> reuse]} {
 read_liberty /OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib
 read_db $reuse/output/flow/results/nangate45/dm173/base/4_cts.odb
 set block [ord::get_db_block]
 foreach net [$block getNets] {
  if {[$net getSigType] in {POWER GROUND} || [$net getName] in {zero_ one_}} {
   puts "INSPECT_NET [$net getName] [$net getSigType] special=[$net isSpecial] iterms=[llength [$net getITerms]] bterms=[llength [$net getBTerms]]"
   if {[$net getName] in {zero_ one_}} {
    foreach pin [$net getITerms] {puts "  TERM [[$pin getInst] getName]/[[$pin getMTerm] getName] [[$pin getMTerm] getIoType]"}
   }
  }
 }
 foreach name {synth_odb.tcl floorplan.tcl global_route.tcl} {
  set f [open /OpenROAD-flow-scripts/flow/scripts/$name r]
  puts "FLOW_SOURCE $name\n[read $f]"
  close $f
 }
}
exit
