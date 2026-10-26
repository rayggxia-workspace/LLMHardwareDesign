"""Generate the approved boundary contract in native Nangate45 command units."""
def generate(budget):
    # The actual Liberty defaults are ns/fF/kOhm. ORFS setRC.tcl uses these
    # units too: keep them instead of changing capacitance to pF globally.
    sdc='set_cmd_units -time ns -capacitance fF -resistance kOhm -distance um\n'
    sdc+='set_units -time ns -capacitance fF -resistance kOhm -distance um\n'
    sdc+='create_clock -name core -period %g [get_ports clk]\n'%budget['clock_ns']
    sdc+='set_clock_uncertainty %g [get_clocks core]\n'%budget['uncertainty_ns']
    sdc+='set_clock_transition %g [get_clocks core]\n'%budget['clock_transition_ns']
    sdc+='set data_inputs {}\nset clock_port [lindex [get_ports clk] 0]\n'
    sdc+='foreach port [all_inputs] { if {$port ne $clock_port} { lappend data_inputs $port } }\n'
    sdc+='set_input_delay -clock core -max %g $data_inputs\n'%budget['input_delay_max_ns']
    sdc+='set_input_delay -clock core -min %g $data_inputs\n'%budget['input_delay_min_ns']
    sdc+='set_output_delay -clock core -max %g [all_outputs]\n'%budget['output_delay_max_ns']
    sdc+='set_output_delay -clock core -min %g [all_outputs]\n'%budget['output_delay_min_ns']
    sdc+='set_driving_cell -lib_cell %s -pin %s $data_inputs\n'%(budget['input_driver']['cell'],budget['input_driver']['pin'])
    sdc+='set_load %g [all_outputs]\n'%(budget['output_load_pf']*1000)
    return sdc
