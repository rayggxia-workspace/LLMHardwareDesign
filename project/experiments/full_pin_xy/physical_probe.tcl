read_db $::env(PINXY_ODB)
foreach pat {*connect* *Wire* *route*} {
  foreach ns {:: ::odb:: ::ord:: ::drt:: ::grt::} {
    puts "API $ns$pat [info commands $ns$pat]"
  }
}
foreach c {check_connectivity check_placement report_wire_length report_tns report_worst_slack report_parasitic_annotation read_spef set_routing_layers} {
  if {[llength [info commands $c]]} {help $c}
}
set n [lindex [[ord::get_db_block] getNets] 0]
catch {$n not_a_method} err
puts "NET_METHODS $err"
puts "PROBE_COMPLETE"
