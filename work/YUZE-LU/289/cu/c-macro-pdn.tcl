add_global_connection -net VDD -inst_pattern {.*} -pin_pattern {^VDD$} -power
add_global_connection -net VSS -inst_pattern {.*} -pin_pattern {^VSS$} -ground
add_global_connection -net VDD -inst_pattern {.*} -pin_pattern {^vdd$} -power
add_global_connection -net VSS -inst_pattern {.*} -pin_pattern {^gnd$} -ground
global_connect
set_voltage_domain -name CORE -power VDD -ground VSS
define_pdn_grid -name parent -voltage_domains CORE -pins metal10
add_pdn_stripe -grid parent -layer metal1 -width 0.17 -pitch 2.4 -offset 0 -followpins
add_pdn_stripe -grid parent -layer metal4 -width 0.48 -pitch 56 -offset 2
add_pdn_stripe -grid parent -layer metal7 -width 1.40 -pitch 30 -offset 2
add_pdn_stripe -grid parent -layer metal10 -width 1.40 -pitch 60 -offset 5
add_pdn_connect -grid parent -layers {metal1 metal4}
add_pdn_connect -grid parent -layers {metal4 metal7}
add_pdn_connect -grid parent -layers {metal7 metal10}
define_pdn_grid -name grid_0 -voltage_domains CORE -macro -cells {local_s_base} -grid_over_pg_pins -halo {2 2 2 2}
add_pdn_connect -grid grid_0 -layers {metal7 metal10}
define_pdn_grid -name grid_1 -voltage_domains CORE -macro -cells {block_v2_e_compact} -grid_over_pg_pins -halo {2 2 2 2}
add_pdn_connect -grid grid_1 -layers {metal7 metal10}
define_pdn_grid -name grid_2 -voltage_domains CORE -macro -cells {block_v2_g} -grid_over_pg_pins -halo {2 2 2 2}
add_pdn_connect -grid grid_2 -layers {metal7 metal10}
define_pdn_grid -name grid_3 -voltage_domains CORE -macro -cells {r_stream_local} -grid_over_pg_pins -halo {2 2 2 2}
add_pdn_connect -grid grid_3 -layers {metal7 metal10}
define_pdn_grid -name grid_4 -voltage_domains CORE -macro -cells {e_s32_pipeline_128} -grid_over_pg_pins -halo {2 2 2 2}
add_pdn_connect -grid grid_4 -layers {metal7 metal10}
define_pdn_grid -name program_bank -voltage_domains CORE -macro -cells {s_sram_256x128_freepdk45} -grid_over_pg_pins -halo {2 2 2 2}
add_pdn_stripe -grid program_bank -layer metal5 -width 0.93 -pitch 10.0 -offset 2
add_pdn_stripe -grid program_bank -layer metal6 -width 0.93 -pitch 10.0 -offset 2
add_pdn_connect -grid program_bank -layers {metal4 metal5}
add_pdn_connect -grid program_bank -layers {metal5 metal6}
add_pdn_connect -grid program_bank -layers {metal6 metal7}
