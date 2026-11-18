read_lef /OpenROAD-flow-scripts/flow/platforms/nangate45/lef/NangateOpenCellLibrary.tech.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/nangate45/lef/NangateOpenCellLibrary.macro.mod.lef
foreach lef $::env(CU_REBASE_LEFS) {read_lef $lef}
read_def $::env(CU_REBASE_DIR)/source.def
source /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/rebase-evidence.tcl
rebase_evidence $::env(CU_REBASE_DIR)/after
foreach kind {geometry instances nets} {
 set f [open $::env(CU_REBASE_DIR)/before-${kind}.tsv];set before [read $f];close $f
 set f [open $::env(CU_REBASE_DIR)/after-${kind}.tsv];set after [read $f];close $f
 if {$before ne $after} {error "New G master reconstruction changed $kind"}
}
write_db $::env(CU_REBASE_TARGET)
puts EXACT_GEOMETRY_PLACEMENT_CONNECTIVITY_REBASE_PASSED
