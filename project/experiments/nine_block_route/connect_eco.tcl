read_db $::env(AUDIT_ODB)
if {![design_is_routed -verbose]} {error "some nets are not routed"}
puts "PASS design_is_routed"
check_antennas -report_file antenna.rpt
