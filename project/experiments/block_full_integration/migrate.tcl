# Qualification of selective route migration, derived copies only.
# The Python adapter owns all paths and runs this under a scheduler allocation.
proc need {key} {
  if {![info exists ::env($key)] || $::env($key) eq ""} {error "Missing $key"}
  return $::env($key)
}
proc targets {} {
  set f [open [need HPY_MIG_TARGETS] r]
  set result {}
  while {[gets $f line] >= 0} {
    if {$line eq ""} {continue}
    dict set result $line 1
  }
  close $f
  if {[dict size $result] == 0} {error "Empty target list"}
  return $result
}
proc write_status {name values} {
  set f [open [file join [need HPY_MIG_OUTPUT] $name] {WRONLY CREAT EXCL}]
  puts $f "key\tvalue"
  foreach {key val} $values {puts $f "$key\t$val"}
  close $f
}
proc check_fixed {selected} {
  set decoder [odb::dbWireDecoder]
  set fixed 0
  set routed 0
  foreach net [[ord::get_db_block] getNets] {
    set wire [$net getWire]
    if {$wire eq "NULL"} {continue}
    set name [$net getName]
    set target [dict exists $selected $name]
    $decoder begin $wire
    set paths 0
    while {1} {
      set op [$decoder next]
      if {$op == 12} {break}
      if {$op in {0 1 2 3}} {
        incr paths
        set typ [$decoder getWireType]
        if {!$target && $typ ne "FIXED"} {error "Non-target path not encoded FIXED: $name $typ"}
        if {$target && $typ ne "ROUTED"} {error "Target path not encoded ROUTED: $name $typ"}
      }
    }
    if {$paths == 0} {error "Wire without decoded paths: $name"}
    if {$target} {incr routed} else {incr fixed}
  }
  rename $decoder ""
  if {$routed != [dict size $selected]} {error "Target ordinary wire count mismatch"}
  return [list fixed_wire_nets $fixed routed_target_nets $routed]
}
proc main {} {
  set stage [need HPY_MIG_STAGE]
  set out [need HPY_MIG_OUTPUT]
  if {![file isdirectory $out]} {error "Output directory missing"}
  set_thread_count 1
  if {$stage in {route rc_sta}} {read_liberty [need HPY_MIG_LIBERTY]}
  read_db [need HPY_MIG_ODB]
  set selected [targets]
  set block [ord::get_db_block]
  foreach name [dict keys $selected] {
    set net [$block findNet $name]
    if {$net eq "NULL"} {error "Target net missing: $name"}
    if {[$net getSigType] in {POWER GROUND}} {error "PG migration excluded: $name"}
  }
  switch -- $stage {
    mark_def {
      set fixed 0
      foreach net [$block getNets] {
        if {[$net getWire] eq "NULL"} {continue}
        if {[dict exists $selected [$net getName]]} {
          $net setWireType ROUTED
        } else {
          $net setWireType FIXED
          incr fixed
        }
      }
      write_def [file join $out marked.def]
      write_status mark.tsv [list fixed_wire_nets $fixed selected_nets [dict size $selected]]
    }
    import_fixed {
      # OpenDB INCREMENTAL mode deliberately skips NETS callbacks. FLOORPLAN
      # mode reads NETS onto the existing block. The input contains headers
      # and NETS ONLY; no cells, rows, pins, die area, or special nets.
      read_def -floorplan_initialize [need HPY_MIG_FIXED_DEF]
      set counts [check_fixed $selected]
      write_db [file join $out prepared.odb]
      write_status prepare.tsv $counts
    }
    route {
      set counts [check_fixed $selected]
      read_sdc [need HPY_MIG_SDC]
      source [need HPY_MIG_WIRE_RC]
      set_routing_layers -signal [need HPY_MIG_SIGNAL_RANGE] -clock [need HPY_MIG_CLOCK_RANGE]
      if {![llength [info commands odb::dbNet_clearGuides]]} {error "Native clearGuides unavailable; stale guides cannot be accepted"}
      foreach net [$block getNets] {$net clearGuides}
      # Only the selected complete ordinary wires may be replaced. Special
      # power wires, physical cells, and all other paths are untouched by us.
      foreach name [dict keys $selected] {
        set net [$block findNet $name]
        set wire [$net getWire]
        if {$wire eq "NULL"} {error "Target wire missing"}
        odb::dbWire_destroy $wire
        grt::add_net_to_route $net
      }
      pin_access
      global_route -guide_file [file join $out selected.guide] -congestion_iterations 50 -critical_nets_percentage 0
      detailed_route -output_drc [file join $out route.drc] \
        -output_guide_coverage [file join $out guide_coverage.csv] \
        -droute_end_iter [need HPY_MIG_DRT_ITERS] -or_seed 55
      # Persist evidence even when the router reports DRCs.
      write_db [file join $out migrated.odb]
      write_def [file join $out migrated.def]
      write_verilog [file join $out migrated.v]
      write_sdc [file join $out migrated.sdc]
      set drvs UNAVAILABLE
      if {[llength [info commands detailed_route_num_drvs]]} {set drvs [detailed_route_num_drvs]}
      write_status route.tsv [list drc_count $drvs geometry_validation separate_native_audit]
    }
    drc {
      if {![llength [info procs drt::check_drc]]} {error "No native drt::check_drc Tcl wrapper"}
      puts "HPY_DRC_PROC_BEGIN"
      puts [info body drt::check_drc]
      puts "HPY_DRC_PROC_END"
      drt::check_drc -output_file [file join $out check.drc]
      write_status drc.tsv [list executed true interpretation requires_report_review]
    }
    rc_sta {
      read_sdc [need HPY_MIG_SDC]
      source [need HPY_MIG_WIRE_RC]
      define_process_corner -ext_model_index 0 HPY_TYP
      extract_parasitics -ext_model_file [need HPY_MIG_RC_RULES]
      write_spef [file join $out extracted.spef]
      read_spef [file join $out extracted.spef]
      report_parasitic_annotation -report_unannotated
      report_checks -path_delay max -format full_clock_expanded -fields {slew cap input nets fanout} -group_path_count 10
      report_checks -path_delay min -format full_clock_expanded -fields {slew cap input nets fanout} -group_path_count 10
      report_check_types -max_slew -max_capacitance -max_fanout -violators
      report_wns
      report_tns
      write_status rc_sta.tsv [list executed true extraction_rules [need HPY_MIG_RC_RULES] interpretation requires_timing_report_review]
    }
    default {error "Unsupported stage: $stage"}
  }
}
try {
  main
} on error {message options} {
  puts stderr "HPY_MIGRATION_ERROR: $message"
  puts stderr [dict get $options -errorinfo]
  exit 1
}
