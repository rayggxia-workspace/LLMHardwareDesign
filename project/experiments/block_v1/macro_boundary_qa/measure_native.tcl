# Native boundary diagnostic collector. Invoked in a fresh STA process.
# No repair, extraction, clock-latency reset or constraint substitution.
proc qa_observe {} {
  foreach library $::env(BV1QA_LIBS) {read_liberty $library}
  if {[info exists ::env(BV1QA_MIN_LIB)] && $::env(BV1QA_MIN_LIB) ne ""} {
    read_liberty -max $::env(BV1QA_MAX_LIB)
    read_liberty -min $::env(BV1QA_MIN_LIB)
  }
  read_verilog $::env(BV1QA_VERILOG)
  link_design $::env(BV1QA_TOP)
  read_sdc $::env(BV1QA_SDC)
  if {$::env(BV1QA_SPEF) ne ""} {read_spef $::env(BV1QA_SPEF)}
  set_propagated_clock [all_clocks]
  sta::find_timing
  set summary [open summary.tsv w]
  puts $summary "time_unit_seconds\t[sta::time_ui_sta 1]"
  puts $summary "capacitance_unit_farads\t[sta::capacitance_ui_sta 1]"
  puts $summary "check_setup\t[check_setup -verbose]"
  puts $summary "setup_violations\t[sta::endpoint_violation_count max]"
  puts $summary "hold_violations\t[sta::endpoint_violation_count min]"
  set ports [open ports.tsv w]
  foreach pin [concat [all_inputs] [all_outputs]] {
    set slew {}
    foreach property {slew_max_rise slew_max_fall slew_min_rise slew_min_fall} {
      lappend slew [get_property $pin $property]
    }
    puts $ports "[get_full_name $pin]\t[string tolower [get_property $pin direction]]\t[join $slew \t]"
  }
  close $ports
  set all_ends [sta::endpoints]
  puts $summary "endpoint_count\t[llength $all_ends]"
  set endpoints [open endpoints.tsv w]
  foreach pin $all_ends {
    set values {}
    foreach property {slack_max_rise slack_max_fall slack_min_rise slack_min_fall} {
      lappend values [get_property $pin $property]
    }
    puts $endpoints "[get_full_name $pin]\t[get_property $pin is_port]\t[string tolower [get_property $pin direction]]\t[join $values \t]"
  }
  close $endpoints
  set observations [open observations.tsv w]
  set observation_count 0
  set input_check_ends {}
  foreach pin $all_ends {
    if {![get_property $pin is_port] && [get_property $pin direction] eq "input"} {
      lappend input_check_ends $pin
    }
  }
  set clock_ports [get_ports clk]
  foreach pin [concat [all_inputs] [all_outputs]] {
    set name [get_full_name $pin]
    set direction [string tolower [get_property $pin direction]]
    if {$direction eq "input" && [lsearch -exact $clock_ports $pin]>=0} {continue}
    if {$direction ni {input output}} {error "Unsupported boundary direction $name"}
    foreach edge {rise fall} {
      foreach analysis {max min} {
        set paths {}
        if {$direction eq "input"} {
          if {[llength $input_check_ends]>0} {
            set paths [find_timing_paths -${edge}_from [list $pin] -to $input_check_ends -path_delay $analysis -group_path_count 1]
          }
        } else {
          set paths [find_timing_paths -${edge}_to [list $pin] -path_delay $analysis -group_path_count 1]
        }
        # One worst path per native path group, then the worst group. This is
        # an aggregate boundary diagnostic, not enumeration of every arc.
        set chosen {}
        foreach path $paths {
          if {$chosen eq "" || [$path slack] < [$chosen slack]} {set chosen $path}
        }
        incr observation_count
        if {$chosen eq ""} {
          puts $observations "$direction\t$name\t$edge\t$analysis\tNO_PATH\t-\t-\t-\t-"
        } else {
          # get_property numeric times are formatted to six decimals by the
          # installed PropertyValue implementation. Native PathEnd methods
          # return numeric SI floats, including the actual check required
          # time (a generic Path point can instead return INF at a D pin).
          set slack [expr {double([$chosen slack])*1e9}]
          set arrival [expr {double([$chosen data_arrival_time])*1e9}]
          set required [expr {double([$chosen data_required_time])*1e9}]
          puts $observations "$direction\t$name\t$edge\t$analysis\t[get_full_name [get_property $chosen startpoint]]\t[get_full_name [get_property $chosen endpoint]]\t$slack\t$arrival\t$required"
        }
      }
    }
  }
  close $observations
  puts $summary "observation_count\t$observation_count"
  foreach kind {capacitance slew fanout} {
    puts $summary "$kind\t[sta::max_${kind}_violation_count]\t[sta::max_${kind}_check_slack]\t[sta::max_${kind}_check_limit]"
  }
  foreach clock [all_clocks] {
    puts $summary "clock\t[get_full_name $clock]\t[get_property $clock is_propagated]\t[get_property $clock period]"
  }
  close $summary
  report_checks -path_delay min_max -group_path_count 10 -digits 12 -format full_clock_expanded > paths.rpt
  report_parasitic_annotation -report_unannotated > annotation.rpt
  write_sdc constraints-readback.sdc
}
if {[catch {qa_observe} problem options]} {
  puts stderr "BV1QA_NATIVE_FAILURE: $problem"
  puts stderr [dict get $options -errorinfo]
  exit 1
}
exit 0
