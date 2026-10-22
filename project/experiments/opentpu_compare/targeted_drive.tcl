# Final route RC may exceed the load seen before legalization. Resize only
# actual offending standard BUF/INV drivers; do not freeze them or alter macros.
set llhd_drive_audit [open [file join $llhd_drive_root targeted-drive.tsv] w]
puts $llhd_drive_audit "round\tinstance\tbefore\tafter"
for {set iteration 0} {$iteration < $llhd_drive_rounds} {incr iteration} {
  estimate_parasitics -global_routing
  set report [file join $llhd_drive_root drive-before-${iteration}.rpt]
  report_check_types -max_capacitance -max_slew -max_count 1000 -digits 9 -no_line_splits > $report
  set f [open $report r]
  set contents [read $f]
  close $f
  set plans [dict create]
  set category ""
  foreach line [split $contents \n] {
    if {$line eq "max capacitance"} {set category cap}
    if {$line eq "max slew"} {set category slew}
    if {![regexp {^\s*(\S+)\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)\s+\((MET|VIOLATED)\)} $line -> pin limit actual slack status]} {continue}
    if {$slack >= 0 || $limit <= 0} {continue}
    set slash [string last / $pin]
    if {$slash < 0} {continue}
    set name [string range $pin 0 [expr {$slash-1}]]
    set inst [[ord::get_db_block] findInst $name]
    if {$inst eq "NULL"} {continue}
    set before [[$inst getMaster] getName]
    if {![regexp {^(BUF|INV)_X(1|2|4|8|16|32)$} $before -> family drive]} {continue}
    set reserve [expr {$category eq "cap" ? 0.65 : 0.80}]
    set required [expr {$drive*$actual/($limit*$reserve)}]
    set target $drive
    while {$target < 32 && $target < $required} {set target [expr {2*$target}]}
    if {$target <= $drive} {continue}
    if {![dict exists $plans $name] || [lindex [dict get $plans $name] 2] < $target} {
      dict set plans $name [list $before $family $target]
    }
  }
  puts "TARGETED_DRIVE_ROUND $iteration upgrades [dict size $plans]"
  if {![dict size $plans]} {break}
  global_route -start_incremental
  dict for {name plan} $plans {
    lassign $plan before family target
    set after ${family}_X${target}
    if {[[ord::get_db] findMaster $after] eq "NULL"} {error "Unavailable legal drive master $after"}
    if {![replace_cell $name $after]} {error "Drive replacement failed on $name"}
    puts $llhd_drive_audit "$iteration\t$name\t$before\t$after"
  }
  detailed_placement_helper
  check_placement -verbose
  global_route -end_incremental
}
close $llhd_drive_audit
estimate_parasitics -global_routing
