set top_odb "$::env(LLHD_ATTEMPT)/flow/results/nangate45/llhd_vec_harness/base/6_final.odb"
read_db $top_odb
set block [ord::get_db_block]
set target [$block findInst u_vec]
if {$target == "NULL" || $target == ""} { error "missing u_vec macro" }
if {[[$target getMaster] getName] != "vec_engine"} { error "unexpected macro master" }
set macros 0
set internal_cells 0
foreach inst [$block getInsts] {
  if {[[$inst getMaster] isBlock]} { incr macros }
  if {[string match "u_vec/*" [$inst getName]]} { incr internal_cells }
}
if {$macros != 1 || $internal_cells != 0} { error "macro re-elaborated or unexpected macro count" }
set out [open "$::env(LLHD_ATTEMPT)/top-physical-inspection.txt" w]
puts $out "macro_count=$macros"
puts $out "vec_internal_cells=$internal_cells"
puts $out "instance=[$target getName]"
puts $out "master=[[$target getMaster] getName]"
puts $out "location_dbu=[$target getLocation]"
puts $out "orientation=[$target getOrient]"
puts $out "placement_status=[$target getPlacementStatus]"
puts $out "dbu_per_um=[$block getDbUnitsPerMicron]"
puts $out "master_size_dbu=[[$target getMaster] getWidth] [[$target getMaster] getHeight]"
puts $out "instance_count=[llength [$block getInsts]]"
close $out
set pins [open "$::env(LLHD_ATTEMPT)/top-interface-pins.tsv" w]
puts $pins "scope\tname\tdirection\tsignal_type\tconnected\tnet"
foreach term [$block getBTerms] {
  set net [$term getNet]
  set connected [expr {$net != "NULL" && $net != ""}]
  set netname ""
  if {$connected} { set netname [$net getName] }
  puts $pins "top\t[$term getName]\t[$term getIoType]\t[$term getSigType]\t$connected\t$netname"
}
foreach term [$target getITerms] {
  set pin [$term getMTerm]
  set net [$term getNet]
  set connected [expr {$net != "NULL" && $net != ""}]
  set netname ""
  if {$connected} { set netname [$net getName] }
  puts $pins "macro\t[$pin getName]\t[$pin getIoType]\t[$pin getSigType]\t$connected\t$netname"
}
close $pins
if {[$target getOrient] != "R0" || [$target getPlacementStatus] != "FIRM"} { error "macro moved or lost fixed placement" }
set expected [expr {80 * [$block getDbUnitsPerMicron]}]
if {[$target getLocation] != [list $expected $expected]} { error "macro moved from its frozen 80 um origin" }
puts "HARDENED_VECTOR_INTEGRATION_STRUCTURE_PASS"
