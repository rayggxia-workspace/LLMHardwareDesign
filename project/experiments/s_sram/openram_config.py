"""Compile ONE bank; the S wrapper instantiates it four times (16 KiB total).

Run with OpenRAM's sram_compiler.py from a dedicated output directory.
Physical integration must use the actual emitted .v/.lib/.lef/.gds/.sp views.
"""
word_size = 128
num_words = 256
num_rw_ports = 1
num_r_ports = 0
num_w_ports = 0
num_banks = 1
words_per_row = 4
write_size = 128
tech_name = "freepdk45"
process_corners = ["TT"]
supply_voltages = [1.1]
temperatures = [25]
output_name = "s_sram_256x128_freepdk45"
output_path = "s_sram_256x128_freepdk45"
check_lvsdrc = True
route_supplies = True
# Use explicitly provisioned tools; never install a toolchain as a side effect.
use_conda = False
# Characterize the actual transistor netlist; analytical estimates are not STA evidence.
analytical_delay = False
spice_name = "ngspice"
drc_name = "klayout"
lvs_name = "klayout"
keep_temp = True
num_threads = 4
num_sim_threads = 1
# Native Cartesian tables, not use_specified_load_slew (whose index handling
# warns upstream). FreePDK45 dff_in_cap=0.2091fF, rise_time=0.005ns:
# loads=0.2091/1.6728/6.6912fF; slews=0.005/0.04/0.16ns.
# The old default 0.8364fF maximum is below Nangate45 DFF_X1 D=1.14029fF
# even before routing. These larger points require actual new simulations;
# never edit an existing Liberty's capacitance limits to hide violations.
load_scales = [1, 8, 32]
slew_scales = [1, 8, 32]
