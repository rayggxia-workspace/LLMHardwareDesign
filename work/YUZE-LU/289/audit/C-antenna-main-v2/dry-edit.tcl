set pkg $::env(C_ANT_ECO_PACKAGE)
read_db $::env(C_ANT_ECO_SOURCE_ODB)
source $pkg/structural-state.tcl
c_ant_original_state original-before.tsv $pkg 0
source $pkg/hook.tcl
c_ant_original_state original-after.tsv $pkg 1
exec cmp original-before.tsv original-after.tsv
write_db candidate.odb
write_def candidate.def
write_verilog candidate.v
puts C_ANTENNA_COPY_ONLY_DRY_EDIT_DONE_NOT_ROUTED_OR_LEGALIZED
