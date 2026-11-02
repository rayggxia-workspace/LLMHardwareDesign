# Delay only measured short data endpoints. Original clocks/SDC are unchanged.
set here [file dirname [file normalize [info script]]]
set block [ord::get_db_block]
set dbu [$block getDbUnitsPerMicron]
set audit [open $here/HOLD_ENDPOINT_ECO.tsv w]
puts $audit "round\tendpoint\tslack_ns\tbuffers"
set serial 0
estimate_parasitics -placement
repair_design -cap_margin 40
repair_timing -setup -setup_margin 0 -skip_buffer_removal -skip_size_down
detailed_placement
check_placement -verbose
estimate_parasitics -placement
for {set round 0} {$round < 6} {incr round} {
 set paths [find_timing_paths -path_delay min -slack_max 0 -group_path_count 1000 -endpoint_path_count 1]
 if {[llength $paths]==0} {break}
 foreach path $paths {
  set pin [get_property $path endpoint]
  set name [get_full_name $pin]
  set slash [string last / $name]
  if {$slash<1 || [string range $name [expr {$slash+1}] end] ne "D"} {error "unhandled hold endpoint $name"}
  set inst [$block findInst [string range $name 0 [expr {$slash-1}]]]
  if {$inst eq "NULL" || ![string match "DFF*" [[$inst getMaster] getName]]} {error "not a DFF data endpoint: $name"}
  set slack [get_property $path slack]
  set count [expr {min(32,max(1,int(ceil((0.035-$slack)/0.025))))}]
  lassign [$inst getLocation] x y
  set location [list [expr {$x/double($dbu)}] [expr {$y/double($dbu)}]]
  for {set i 0} {$i<$count} {incr i} {
   if {$serial>=5000} {error "targeted hold ECO exceeded 5000-cell guard"}
   set bn [format "r166_hold_endpoint_%05d" $serial]
   insert_buffer -buffer_cell CLKBUF_X1 -load_pins [list $pin] -location $location -buffer_name $bn -net_name ${bn}_net
   incr serial
  }
  puts $audit "$round\t$name\t$slack\t$count"
 }
 unset_dont_touch [get_cells r166_hold_endpoint_*]
 add_global_connection -net VDD -inst_pattern {r166_hold_endpoint_.*} -pin_pattern {VDD} -power
 add_global_connection -net VSS -inst_pattern {r166_hold_endpoint_.*} -pin_pattern {VSS} -ground
 global_connect
 set_dont_touch [get_cells r166_hold_endpoint_*]
 detailed_placement
 check_placement -verbose
 estimate_parasitics -placement
}
close $audit
# Mirror optimization can move fence-edge cells; legalize after all ECO operations.
detailed_placement
check_placement -verbose
unset_dont_touch [get_cells r166_hold_endpoint_*]
global_connect
set_dont_touch [get_cells r166_hold_endpoint_*]
estimate_parasitics -placement
report_worst_slack -min
report_worst_slack -max
puts "R166_TARGETED_ENDPOINT_DELAY_BUFFERS=$serial"
