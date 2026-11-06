read_db $::env(GATE_DB)
set_thread_count $::env(SLURM_CPUS_PER_TASK)
extract_parasitics -ext_model_file /OpenROAD-flow-scripts/flow/platforms/nangate45/rcx_patterns.rules
write_spef candidate.spef
write_abstract_lef candidate.lef
report_design_area
foreach name {VDD VSS} {
    check_power_grid -net $name -error_file pg-$name.rpt
}
