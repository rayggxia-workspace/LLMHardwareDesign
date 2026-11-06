read_db $::env(P_ODB)
read_liberty /OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib
set_thread_count $::env(SLURM_CPUS_PER_TASK)
set block [ord::get_db_block]
set db [ord::get_db]
set m10 [[$db getTech] findLayer metal10]
set strength $::env(P_STRENGTH)
set master [$db findMaster BUF_X$strength]
if {$master eq "NULL"} { error "missing BUF_X$strength" }
remove_fillers
foreach inst [$block getInsts] {
    if {[$inst isPlaced]} { $inst setPlacementStatus LOCKED }
}
set repeater [odb::dbInst_create $block $master upper_valid_repeater]
set x 4000190
set y $::env(P_RELAY_Y)
$repeater setLocation $x $y
$repeater setPlacementStatus PLACED
foreach {suffix io pin dx dy} {in INPUT A 0 0 out OUTPUT Z 16000 16000} {
    set name upper_valid_$suffix
    set net [odb::dbNet_create $block $name]
    set bterm [odb::dbBTerm_create $net $name]
    $bterm setIoType $io
    $bterm setSigType SIGNAL
    set bpin [odb::dbBPin_create $bterm]
    $bpin setPlacementStatus FIRM
    odb::dbBox_create $bpin $m10 [expr {$x+$dx-2000}] [expr {$y+$dy-2000}] [expr {$x+$dx+2000}] [expr {$y+$dy+2000}]
    odb::dbITerm_connect [$repeater findITerm $pin] $net
}
global_connect
detailed_placement -max_displacement {80 80}
check_placement -verbose
write_db eco-placed.odb
set_routing_layers -signal metal1-metal10
set_nets_to_route {upper_valid_in upper_valid_out}
global_route -allow_congestion -congestion_iterations 10 -guide_file eco.guide
detailed_route -droute_end_iter 12 -output_drc eco-drc.rpt -via_in_pin_bottom_layer metal10 -via_in_pin_top_layer metal10
filler_placement {FILLCELL_X32 FILLCELL_X16 FILLCELL_X8 FILLCELL_X4 FILLCELL_X2 FILLCELL_X1}
global_connect
write_db eco-routed.odb
write_def eco-routed.def
write_verilog eco-routed.v
