# Experimental drive-only ECO: retain incoming regular wires whose endpoints
# did not move or change master. Native DRT may still repair any retained wire.
# All final extraction, DRC, connectivity, PG, timing and proof gates still apply.
proc llhd_route_reuse_snapshot {} {
  set states [dict create]
  foreach inst [[ord::get_db_block] getInsts] {
    set connections {}
    foreach term [$inst getITerms] {
      set net [$term getNet]
      if {$net eq "NULL" || [$net getSigType] in {POWER GROUND}} {continue}
      lappend connections [list [[$term getMTerm] getName] [$net getName]]
    }
    dict set states [$inst getName] [list [[$inst getMaster] getName] \
      {*}[$inst getLocation] [$inst getOrient] [lsort $connections]]
  }
  return $states
}

proc llhd_route_reuse_clear_changed {before root} {
  set after [llhd_route_reuse_snapshot]
  if {[lsort [dict keys $before]] ne [lsort [dict keys $after]]} {
    error "Route reuse pilot supports drive-only changes, without added/deleted instances"
  }
  set changed 0
  set dirty [dict create]
  set f [open [file join $root route-reuse-instances.tsv] w]
  puts $f "instance\tbefore_master\tbefore_x\tbefore_y\tbefore_orient\tafter_master\tafter_x\tafter_y\tafter_orient"
  dict for {name state} $after {
    set old [dict get $before $name]
    if {[lindex $state 4] ne [lindex $old 4]} {
      error "Route reuse pilot forbids changed signal connectivity: $name"
    }
    if {$state eq $old} {continue}
    incr changed
    puts $f [join [list $name {*}[lrange $old 0 3] {*}[lrange $state 0 3]] \t]
    foreach term [[[ord::get_db_block] findInst $name] getITerms] {
      set net [$term getNet]
      if {$net ne "NULL" && [$net getSigType] ni {POWER GROUND}} {
        dict set dirty [$net getName] $net
      }
    }
  }
  close $f
  set cleared 0
  set f [open [file join $root route-reuse-nets.tsv] w]
  puts $f "net\tcleared_regular_wire"
  dict for {name net} $dirty {
    set wire [$net getWire]
    set present [expr {$wire ne "NULL"}]
    puts $f "$name\t$present"
    if {$present} {odb::dbWire_destroy $wire;incr cleared}
  }
  close $f
  set retained 0
  foreach net [[ord::get_db_block] getNets] {
    if {[$net getSigType] ni {POWER GROUND} && [$net getWire] ne "NULL"} {incr retained}
  }
  if {$changed == 0 || $cleared == 0 || $retained == 0} {error "Empty route reuse experiment"}
  set f [open [file join $root route-reuse-summary.tsv] w]
  puts $f "changed_instances\taffected_nets\tcleared_regular_wires\tretained_incoming_regular_wires"
  puts $f "$changed\t[dict size $dirty]\t$cleared\t$retained"
  close $f
  puts "ROUTE_REUSE changed_instances=$changed affected_nets=[dict size $dirty] cleared=$cleared retained=$retained"
}
