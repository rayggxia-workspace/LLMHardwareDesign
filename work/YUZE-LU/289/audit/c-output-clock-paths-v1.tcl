# Read-only clock insertion evidence for two independently failing output paths.
set_thread_count 8
set root /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117
set seed $root/audit/C-v28-nine-net-normalization-v1/reextract-encoder
set source_results $root/cu/runs/C-v28-actual-i8-h50/flow/results/nangate45/c-overlay-current/base
read_liberty /OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib
foreach lib $::env(CU_LIBS) {read_liberty $lib}
read_db $seed/before.odb
read_sdc $source_results/6_final.sdc
read_spef $seed/isolated.spef
set_propagated_clock [all_clocks]
sta::find_timing
report_checks -to [get_ports {trace_retire_o}] -path_delay max -group_path_count 1 -format full_clock_expanded -fields {slew cap fanout input_pin net} -digits 9 > trace-full-clock.rpt
report_checks -to [get_ports {mem_wr_address[63]}] -path_delay max -group_path_count 1 -format full_clock_expanded -fields {slew cap fanout input_pin net} -digits 9 > write-full-clock.rpt
set block [ord::get_db_block]
set wanted [list {control.task_packet[66]$_DFFE_PN0P_} {memory_service.memory.transfer.save.write_issued[1]$_SDFFE_PN0P_}]
set lookup {}
foreach inst [$block getInsts] {
 set name [string map [list "\\" ""] [$inst getName]]
 if {$name in $wanted} {dict set lookup $name $inst}
}
if {[dict size $lookup] != 2} {error "Missing launch instance"}
set out [open clock-backtrace.tsv w]
puts $out "launch\tdepth\tnet\tdriver\tmaster\txy\tsinks\tinput_pin"
foreach launch $wanted {
 set inst [dict get $lookup $launch]
 set pin [$inst findITerm CK]
 if {$pin eq "NULL"} {error "Missing launch CK $launch"}
 set seen {}
 for {set depth 0} {$depth < 100} {incr depth} {
  set net [$pin getNet]
  if {$net eq "NULL"} {error "Disconnected clock backtrace $launch"}
  set name [$net getName]
  if {[dict exists $seen $name]} {error "Clock cycle in backtrace"}
  dict set seen $name 1
  set drivers {};set sinks 0
  foreach it [$net getITerms] {
   if {[[$it getMTerm] getIoType] eq "OUTPUT"} {lappend drivers $it} else {incr sinks}
  }
  if {![llength $drivers]} {
   puts $out [join [list $launch $depth $name ROOT INPUT {} $sinks {}] "\t"]
   break
  }
  if {[llength $drivers] != 1} {error "Clock net has ambiguous drivers $name"}
  set driver [lindex $drivers 0];set inst [$driver getInst];set master [$inst getMaster]
  set inputs {}
  foreach it [$inst getITerms] {
   if {[[$it getMTerm] getIoType] eq "INPUT" && [[$it getMTerm] getSigType] ni {POWER GROUND}} {lappend inputs $it}
  }
  puts $out [join [list $launch $depth $name [$inst getName] [$master getName] [$inst getLocation] $sinks [join [lmap it $inputs {[$it getMTerm] getName}] ,]] "\t"]
  if {[$master isBlock] || [llength $inputs] != 1 || ![regexp {^(CLKBUF|BUF|INV)_X[0-9]+$} [$master getName]]} {
   puts $out "# Non-simple clock element: stopped without inferring a common root."
   break
  }
  set pin [lindex $inputs 0]
 }
}
close $out
puts READ_ONLY_OUTPUT_CLOCK_DIAGNOSTIC_NO_CLOCK_OR_CONSTRAINT_EDIT
