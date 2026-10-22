# Final route RC may exceed the load seen before legalization. Resize only
# actual offending standard BUF/INV drivers; do not freeze them or alter macros.
if {![info exists llhd_drive_phase]} {set llhd_drive_phase initial}
set llhd_drive_audit [open [file join $llhd_drive_root targeted-drive-${llhd_drive_phase}.tsv] w]
puts $llhd_drive_audit "round\tinstance\tbefore\tafter"
set llhd_guard_audit [open [file join $llhd_drive_root macro-output-guards-${llhd_drive_phase}.tsv] w]
puts $llhd_guard_audit "round\tpin\tinstance\tmaster\tside\tx_um\ty_um"
if {![info exists llhd_guarded]} {set llhd_guarded [dict create]}
for {set iteration 0} {$iteration < $llhd_drive_rounds} {incr iteration} {
  estimate_parasitics -global_routing
  set report [file join $llhd_drive_root drive-before-${llhd_drive_phase}-${iteration}.rpt]
  report_check_types -max_capacitance -max_slew -max_count 1000 -digits 9 -no_line_splits > $report
  set f [open $report r]
  set contents [read $f]
  close $f
  set plans [dict create]
  set guards [dict create]
  set category ""
  foreach line [split $contents \n] {
    if {$line eq "max capacitance"} {set category cap}
    if {$line eq "max slew"} {set category slew}
    if {![regexp {^\s*(\S+)\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)\s+\((MET|VIOLATED)\)} $line -> pin limit actual slack status]} {continue}
    if {$limit <= 0} {continue}
    set reserve [expr {$category eq "cap" ? 0.65 : 0.80}]
    set guarded [expr {[info exists llhd_drive_guardband] && $llhd_drive_guardband}]
    if {$slack >= 0 && (!$guarded || $actual <= $limit*$reserve)} {continue}
    set slash [string last / $pin]
    if {$slash < 0} {continue}
    set name [string range $pin 0 [expr {$slash-1}]]
    set inst [[ord::get_db_block] findInst $name]
    if {$inst eq "NULL"} {continue}
    set port [string range $pin [expr {$slash+1}] end]
    set term [$inst findITerm $port]
    if {$term eq "NULL"} {continue}
    # Slew is reported at the receiving macro pin too. Resize its actual
    # standard driver, never change the immutable macro's liberty model.
    if {[$term getIoType] eq "INPUT"} {
      set net [$term getNet]
      if {$net eq "NULL"} {continue}
      set driver "NULL"
      foreach candidate [$net getITerms] {
        if {[$candidate getIoType] eq "OUTPUT"} {
          set driver [$candidate getInst];set term $candidate
          set pin "[$driver getName]/[[$candidate getMTerm] getName]"
          break
        }
      }
      if {$driver eq "NULL"} {continue}
      set inst $driver;set name [$inst getName]
    }
    set before [[$inst getMaster] getName]
    if {[info exists llhd_enable_macro_guards] && $llhd_enable_macro_guards && [string match llhd_* $before]} {
      if {[$term getIoType] eq "OUTPUT" && ![dict exists $llhd_guarded $pin]} {dict set guards $pin 1}
      continue
    }
    if {![regexp {^(BUF|INV)_X(1|2|4|8|16|32)$} $before -> family drive]} {continue}
    set required [expr {$drive*$actual/($limit*$reserve)}]
    set target $drive
    while {$target < 32 && $target < $required} {set target [expr {2*$target}]}
    if {$target <= $drive} {continue}
    if {![dict exists $plans $name] || [lindex [dict get $plans $name] 2] < $target} {
      dict set plans $name [list $before $family $target]
    }
  }
  puts "TARGETED_DRIVE_ROUND $iteration upgrades [dict size $plans] macro_output_guards [dict size $guards]"
  set llhd_drive_change_count [expr {[dict size $plans]+[dict size $guards]}]
  if {![dict size $plans] && ![dict size $guards]} {break}
  set checkpoint_only [expr {[info exists llhd_drive_checkpoint_only] && $llhd_drive_checkpoint_only}]
  if {!$checkpoint_only} {global_route -start_incremental}
  dict for {pin unused} $guards {
    set record [llhd_guard_macro_output $pin [dict size $llhd_guarded]]
    dict set llhd_guarded $pin $record
    puts $llhd_guard_audit "$iteration\t[join $record \t]"
  }
  dict for {name plan} $plans {
    lassign $plan before family target
    set after ${family}_X${target}
    if {[[ord::get_db] findMaster $after] eq "NULL"} {error "Unavailable legal drive master $after"}
    if {![replace_cell $name $after]} {error "Drive replacement failed on $name"}
    puts $llhd_drive_audit "$iteration\t$name\t$before\t$after"
  }
  global_connect
  detailed_placement_helper
  check_placement -verbose
  # A checkpoint-only pass never estimates the mutated, in-memory routes.
  # The next process rebuilds routes/RC from the legalized ODB instead.
  if {$checkpoint_only} {break}
  global_route -end_incremental
  if {[info exists llhd_drive_full_route] && $llhd_drive_full_route} {
    global_route -congestion_iterations 30
  }
}
close $llhd_drive_audit
close $llhd_guard_audit
if {![info exists llhd_drive_checkpoint_only] || !$llhd_drive_checkpoint_only} {estimate_parasitics -global_routing}
