# Single-corner reports for this direct macro harness. The source/block input
# and output delay budgets are not added together to infer a system frequency.
check_setup -verbose > $::env(LLHD_ATTEMPT)/top-check-setup.rpt
report_clock_properties [all_clocks] > $::env(LLHD_ATTEMPT)/top-clocks.rpt
report_checks -path_delay min_max -group_path_count 20 -unconstrained > $::env(LLHD_ATTEMPT)/top-paths.rpt
report_check_types -max_slew -max_capacitance -max_fanout -violators > $::env(LLHD_ATTEMPT)/top-electrical.rpt
