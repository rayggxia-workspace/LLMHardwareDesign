# Read-only full-context access probe: no global or detailed routing.
set_thread_count $::env(CU_PROBE_CORES)
read_db $::env(CU_PROBE_ODB)
set_routing_layers -signal metal2-metal10 -clock metal2-metal10
pin_access -via_in_pin_bottom_layer metal10 -via_in_pin_top_layer metal10 -via_access_layer metal10 -verbose 1
puts STRICT_METAL10_PIN_ACCESS_PASSED
