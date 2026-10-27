read_liberty {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/leaf_timing_models/r03/act-A_child_replay/timing.lib}
set f [open {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/leaf_timing_models/r03/act-A_child_replay/model_pins.tsv} w]
puts $f "pin\tdirection"
foreach p [get_lib_pins -of_objects [get_lib_cells *]] {puts $f "[get_full_name $p]\t[get_property $p direction]"}
close $f
