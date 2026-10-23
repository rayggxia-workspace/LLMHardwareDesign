# Geometry-only view of the completed block. Liberty is copied, not regenerated.
set result $::env(LLHD_BLOCK)/flow/results/nangate45/llhd_vec_original/base
read_db $result/6_final.odb
set bloat 0
if { $::env(LLHD_MACRO_PDN) == "guarded-m10" } { set bloat 1 }
puts "EXPLICIT ABSTRACT LEF BLOAT_FACTOR $bloat"
write_abstract_lef -bloat_factor $bloat $::env(LLHD_MACRO_VIEW)/vec_engine.lef
