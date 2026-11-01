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
