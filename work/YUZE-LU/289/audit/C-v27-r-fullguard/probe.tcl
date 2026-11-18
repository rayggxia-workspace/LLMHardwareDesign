read_db /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/runs/C-v27-joint-e20-h30/flow/results/nangate45/c-overlay-current/base/6_final.odb
source /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/C-final-v1/geometry-all.tcl
set before [geometry_snapshot before-geometry.tsv]
write_verilog before.v
source hook.tcl
if {$kg_added!=$kg_expected_count} {error "Unexpected first append count"}
source hook.tcl
if {$kg_added!=0} {error "Not idempotent"}
if {[geometry_snapshot after-geometry.tsv] ne $before} {error "Interface geometry changed"}
write_verilog after.v
exec cmp before.v after.v
puts C_SPACING_KEEPOUT_GEOMETRY_LOGIC_IDEMPOTENCE_PASS
help pin_access
