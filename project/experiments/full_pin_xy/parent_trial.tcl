# NEW controlled parent access experiment; never a reconstruction of old handoff.
# routing_only.lib carries port declarations, not characterized timing models.
set out $::env(PINXY_PARENT_OUT)
set stages [open $out/stages.tsv w];puts $stages "stage\tstatus\tdetail"
proc stage {name body} {
  global stages
  puts "STAGE_START $name"
  if {[catch {uplevel 1 $body} result options]} {
    puts $stages "$name\tFAIL\t[string map [list \n { | } \t { }] $result]";flush $stages
    set f [open "$::env(PINXY_PARENT_OUT)/$name.error.txt" w];puts $f [dict get $options -errorinfo];close $f
    puts "STAGE_FAIL $name $result";return 0
  }
  puts $stages "$name\tEXECUTED\t";flush $stages;puts "STAGE_EXECUTED $name";return 1
}
proc parent_contract {prefix} {
  set b [ord::get_db_block]
  set f [open "$prefix.instances.tsv" w];puts $f "instance\tmaster\tx\ty\torientation"
  foreach i [$b getInsts] {lassign [$i getLocation] x y;puts $f [join [list [$i getName] [[$i getMaster] getName] $x $y [$i getOrient]] "\t"]};close $f
  set f [open "$prefix.endpoints.tsv" w];puts $f "kind\tinstance\tpin\tnet\tdirection\tlayer"
  foreach n [$b getNets] {
    if {[$n getSigType] in {POWER GROUND}} {continue}
    foreach it [$n getITerms] {
      set ls {};foreach g [$it getGeometries] {lappend ls [[lindex $g 0] getName]}
      puts $f [join [list ITERM [[$it getInst] getName] [[$it getMTerm] getName] [$n getName] [$it getIoType] [join [lsort -unique $ls] ,]] "\t"]
    }
    foreach bt [$n getBTerms] {
      set ls {};foreach bp [$bt getBPins] {foreach box [$bp getBoxes] {lappend ls [[$box getTechLayer] getName]}}
      puts $f [join [list BTERM {} [$bt getName] [$n getName] [$bt getIoType] [join [lsort -unique $ls] ,]] "\t"]
    }
  };close $f
  set f [open "$prefix.pins.tsv" w];puts $f "pin\tdirection\tuse\tnet\tlayer\tx0\ty0\tx1\ty1"
  foreach bt [$b getBTerms] {foreach bp [$bt getBPins] {foreach box [$bp getBoxes] {puts $f [join [list [$bt getName] [$bt getIoType] [$bt getSigType] [[$bt getNet] getName] [[$box getTechLayer] getName] [$box xMin] [$box yMin] [$box xMax] [$box yMax]] "\t"]}}};close $f
  set f [open "$prefix.pdn.tsv" w]
  foreach n [$b getNets] {foreach sw [$n getSWires] {foreach r [$sw getWires] {
    set via {};set xy {}
    if {[$r isVia]} {set v [$r getTechVia];if {$v eq "NULL"} {set v [$r getBlockVia]};set via [$v getName];set layer VIA;set xy [$r getViaXY]} else {set layer [[$r getTechLayer] getName]}
    puts $f [join [list [$n getName] $layer [$r xMin] [$r yMin] [$r xMax] [$r yMax] $via $xy] "\t"]
  }}};close $f
}
if {![stage load {
  read_liberty /OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib
  read_liberty $::env(PINXY_PARENT_INPUT)/routing_only.lib
  source $::env(PINXY_PARENT_RUN_SETUP)
}]} {catch {write_db $out/failed-load.odb};close $stages;exit 1}
if {![stage placement_and_contract {check_placement -verbose;parent_contract $out/before;write_db $out/placed.odb}]} {close $stages;exit 1}
set vdd_ok [stage pdn_check_VDD {check_power_grid -net VDD -error_file $out/VDD.pdn.rpt}]
set vss_ok [stage pdn_check_VSS {check_power_grid -net VSS -error_file $out/VSS.pdn.rpt}]
if {!$vdd_ok || !$vss_ok} {
  write_db $out/failed-PG.odb
  parent_contract $out/after
  puts "FAILED_PARENT_PG_GATE; do not attempt a qualified signal route on invalid power geometry"
  close $stages;exit 1
}
if {![stage global_route {
  set_routing_layers -signal metal2-metal10 -clock metal4-metal10
  global_route -guide_file $out/route.guide -congestion_report_file $out/congestion.rpt
  write_db $out/global.odb
}]} {close $stages;exit 1}
if {![stage detailed_route {
  detailed_route -output_drc $out/route.drc -output_maze $out/maze.log -verbose 1
  write_db $out/routed.odb;write_def $out/routed.def
}]} {close $stages;exit 1}
stage terminal_contract {parent_contract $out/after}
stage wire_statistics {report_wire_length -detailed_route -summary -file $out/wire_length.csv}
stage all_signal_access_export {
  set ::env(PINXY_ACCESS_ALL) 1;set ::env(PINXY_ACCESS_OUT) $out/whole_access.tsv.gz
  source $::env(PINXY_DRIVER)/export_access.tcl
}
stage pdn_final_VDD {check_power_grid -net VDD -error_file $out/final_VDD.pdn.rpt}
stage pdn_final_VSS {check_power_grid -net VSS -error_file $out/final_VSS.pdn.rpt}
# No parent STA or electrical "pass" is produced from uncharacterized stubs.
puts "PARENT_ROUTING_STAGES_FINISHED_NOT_FULL_QUALIFICATION"
close $stages
