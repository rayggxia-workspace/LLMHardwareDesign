read_db $::env(GRAFT_TARGET)
source geometry-all.tcl
geometry_snapshot apply-before-geometry.tsv
write_verilog apply-before.v
source generated/hook.tcl
geometry_snapshot apply-after-geometry.tsv
exec cmp apply-before-geometry.tsv apply-after-geometry.tsv
write_db results/6_final.odb
write_def results/6_final.def
write_verilog results/6_final.v
exec cmp apply-before.v results/6_final.v
