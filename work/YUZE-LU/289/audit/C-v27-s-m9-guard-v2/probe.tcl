set_thread_count 8
read_db /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/runs/C-v27-joint-e20-h30/flow/results/nangate45/c-overlay-current/base/6_final.odb
source /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/C-final-v1/geometry-all.tcl
set before [geometry_snapshot before-geometry.tsv]
write_verilog before.v
source hook.tcl
if {$::c_s_m9_guard::added!=1 || $::c_s_m9_guard::ripped!=1} {error "Expected one new guard / one rip"}
source hook.tcl
if {$::c_s_m9_guard::added!=0 || $::c_s_m9_guard::ripped!=0} {error "Not idempotent"}
write_verilog after.v
exec cmp before.v after.v
if {[geometry_snapshot after-geometry.tsv] ne $before} {error "Geometry changed"}
write_db dry-edit.odb
puts C_S_M9_STRUCTURAL_PASS
set_routing_layers -signal metal2-metal10 -clock metal4-metal10
pin_access -via_in_pin_bottom_layer metal10 -via_in_pin_top_layer metal10 -via_access_layer metal10 -verbose 1
puts C_S_M9_STATIC_ACCESS_PASS_REQUIRES_ACTUAL_ROUTE
