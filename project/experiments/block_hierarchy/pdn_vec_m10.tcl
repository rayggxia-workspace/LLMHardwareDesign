# H1: add a parent M10 resource above the already routed VECTOR.
# Original macro signal/PG geometry and all detailed OBS are retained.
add_global_connection -net VDD -inst_pattern {.*} -pin_pattern {^VDD$} -power
add_global_connection -net VSS -inst_pattern {.*} -pin_pattern {^VSS$} -ground
global_connect
set_voltage_domain -name CORE -power VDD -ground VSS

define_pdn_grid -name parent_grid -voltage_domains CORE -pins metal10
add_pdn_stripe -grid parent_grid -layer metal1 -width 0.17 -pitch 2.4 -offset 0 -followpins
add_pdn_stripe -grid parent_grid -layer metal4 -width 0.48 -pitch 56 -offset 2
add_pdn_stripe -grid parent_grid -layer metal7 -width 1.40 -pitch 30 -offset 2
add_pdn_stripe -grid parent_grid -layer metal10 -width 1.40 -pitch 30 -offset 2
add_pdn_connect -grid parent_grid -layers {metal1 metal4}
add_pdn_connect -grid parent_grid -layers {metal4 metal7}
add_pdn_connect -grid parent_grid -layers {metal7 metal10}

# Use existing macro M7 POWER/GROUND shapes; no macro M5/M6 straps.
# PDNGEN must find legal via stacks through the detailed M8/M9 obstructions.
define_pdn_grid -name vec_pg_access -voltage_domains CORE -macro \
  -instances u_vec -grid_over_pg_pins -halo {2 2 2 2}
add_pdn_connect -grid vec_pg_access -layers {metal7 metal10}
