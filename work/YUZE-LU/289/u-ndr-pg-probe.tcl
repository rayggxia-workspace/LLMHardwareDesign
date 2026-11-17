# Read-only source experiments; any edits remain in memory. No acceptance output.
set_thread_count 8
set mode $::env(PROBE_MODE)
read_db $::env(PROBE_SOURCE)
set b [ord::get_db_block];set tech [ord::get_db_tech]
set chosen {}
foreach net [$b getNets] {
 if {[string map [list "\\" ""] [$net getName]] eq {datapath.legacy_rsp_data[90]}} {lappend chosen $net}
}
if {[llength $chosen]!=1} {error "Ambiguous probe net"}
set net [lindex $chosen 0]
if {$mode in {create assign rip}} {
 set widths {};set spacings {}
 foreach l [$tech getLayers] {
  if {[$l getType] ne "ROUTING"} {continue}
  set name [$l getName];set gap [$l getSpacing]
  if {$name eq "metal9"} {set gap [ord::microns_to_dbu 1.2]}
  lappend widths $name [ord::dbu_to_microns [$l getWidth]]
  lappend spacings $name [ord::dbu_to_microns $gap]
 }
 create_ndr -name probe_native_width_upper_spacing -width $widths -spacing $spacings
 set rules {}
 foreach r [$b getNonDefaultRules] {if {[$r getName] eq "probe_native_width_upper_spacing"} {lappend rules $r}}
 if {[llength $rules]!=1} {error "Missing probe rule"}
 set r [lindex $rules 0];$r setHardSpacing 1
 if {$mode in {assign rip}} {$net setNonDefaultRule $r}
 if {$mode eq "rip"} {set w [$net getWire];if {$w ne "NULL"} {odb::dbWire_destroy $w}}
}
if {$mode eq "finalstrip"} {
 # Diagnostic only: rule metadata removal, without claiming wire interpretation is unchanged.
 $net setNonDefaultRule NULL
}
puts "PROBE_MODE $mode NET [$net getName] NDR [$net getNonDefaultRule]"
foreach rail {VDD VSS} {
 set rc [catch {check_power_grid -net $rail} result]
 puts "PROBE_PG_RESULT $mode $rail CATCH=$rc RESULT=$result"
}
puts DIAGNOSTIC_ONLY_NO_SOURCE_FILES_WRITTEN
