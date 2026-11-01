# Introspect the actual installed receiver APIs; no design is optimized.
foreach cmd {report_checks report_worst_slack report_tns report_check_types
             report_parasitic_annotation check_setup check_power_grid
             report_clock_min_period write_spef write_verilog write_abstract_lef
             all_registers all_outputs get_property get_full_name} {
  help $cmd
}
foreach pattern {sta::*endpoint* sta::*slack* sta::*capacitance* sta::*slew* sta::*fanout*} {
  puts "API $pattern [lsort [info commands $pattern]]"
}
foreach name {sta::report_check_types sta::report_capacitance_checks
              sta::report_slew_checks sta::report_fanout_checks
              sta::report_parasitic_annotation sta::check_setup
              sta::report_worst_slack sta::report_checks} {
  if {[llength [info procs $name]]} {
    puts "PROC_BEGIN $name"
    puts [info args $name]
    puts [info body $name]
    puts "PROC_END $name"
  }
}
