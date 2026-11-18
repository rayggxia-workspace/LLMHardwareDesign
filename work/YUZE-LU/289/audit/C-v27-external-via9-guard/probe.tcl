set_thread_count 8
read_db /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/runs/C-v27-joint-e20-h30/flow/results/nangate45/c-overlay-current/base/6_final.odb
source /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/C-final-v1/geometry-all.tcl
set before [geometry_snapshot before-geometry.tsv]
write_verilog before.v
source hook.tcl
if {$::c_external_via9_guard::added!=2 || $::c_external_via9_guard::ripped!=4} {error "Expected initial 2 keepouts / 4 ripped wires"}
source hook.tcl
if {$::c_external_via9_guard::added!=0 || $::c_external_via9_guard::ripped!=0} {error "Guard not idempotent"}
write_verilog after.v
exec cmp before.v after.v
if {[geometry_snapshot after-geometry.tsv] ne $before} {error "Boundary geometry changed"}
puts EXTERNAL_VIA9_STRUCTURAL_PASS
set_routing_layers -signal metal2-metal10 -clock metal4-metal10
pin_access -via_in_pin_bottom_layer metal10 -via_in_pin_top_layer metal10 -via_access_layer metal10 -verbose 1
puts EXTERNAL_VIA9_STATIC_ACCESS_PASS_REQUIRES_ACTUAL_ROUTE
