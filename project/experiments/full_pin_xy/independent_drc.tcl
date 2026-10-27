# New process, no router cache from a preceding detailed_route command.
read_db $::env(PINXY_DRC_ODB)
set_routing_layers -signal metal2-metal$::env(PINXY_TOP_LAYER) -clock metal4-metal$::env(PINXY_TOP_LAYER)
drt::check_drc -output_file $::env(PINXY_DRC_OUT)
puts "INDEPENDENT_DRC_EXECUTED"
