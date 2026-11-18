read_db $::env(CU_REBASE_SOURCE)
source /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/rebase-evidence.tcl
rebase_evidence $::env(CU_REBASE_DIR)/before
write_def $::env(CU_REBASE_DIR)/source.def
write_verilog $::env(CU_REBASE_DIR)/source.v
