set_thread_count 16
foreach pattern {odb::*dbWireEncoder* odb::*dbWireDecoder* odb::*dbWire_*} {
  puts "API_PATTERN $pattern"
  puts [join [lsort [info commands $pattern]] "\n"]
}
if {[llength [info commands odb::new_dbWireEncoder]] != 1} {
  error "Pinned tool has no exposed wire encoder constructor"
}
set encoder [odb::new_dbWireEncoder]
puts "ENCODER_OBJECT $encoder"
puts "ENCODER_DISPATCH [info commands $encoder]"
odb::delete_dbWireEncoder $encoder
puts PINNED_API_PROBE_PASS
