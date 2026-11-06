# Keep accepted instances and wires fixed. Add only a final drive stage per output.
read_db $::env(ECO_ODB)
foreach lib $::env(ECO_LIBS) { read_liberty $lib }
read_sdc $::env(ECO_SDC)
set block [ord::get_db_block]
set strength $::env(ECO_STRENGTH)
set master [[ord::get_db] findMaster BUF_X$strength]
if {$master eq "NULL"} { error "missing BUF_X$strength" }
set file [open $::env(ECO_PORTS) r]
set lines [split [string trim [read $file]] "\n"]
close $file
remove_fillers
set affected {}
foreach i [$block getInsts] {
    if {[$i isPlaced]} { $i setPlacementStatus LOCKED }
}
set serial 0
foreach row $lines {
    lassign $row name load
    set terminal [$block findBTerm $name]
    if {$terminal eq "NULL"} { error "missing port $name" }
    set net [$terminal getNet]
    set driver ""
    foreach it [$net getITerms] {
        if {[$it getIoType] eq "OUTPUT"} {
            if {$driver ne ""} { error "multiple drivers of $name" }
            set driver $it
        }
    }
    if {$driver eq "" || [[[$driver getInst] getMaster] getName] ne "BUF_X4"} {
        error "unexpected output driver $name"
    }
    set orig [$driver getInst]
    set instance [odb::dbInst_create $block $master eco_relay_$serial]
    lassign [$orig getLocation] x y
    $instance setOrient [$orig getOrient]
    $instance setLocation $x $y
    $instance setPlacementStatus PLACED
    set mid [odb::dbNet_create $block eco_feed_$serial]
    odb::dbITerm_disconnect $driver
    odb::dbITerm_connect $driver $mid
    odb::dbITerm_connect [$instance findITerm A] $mid
    odb::dbITerm_connect [$instance findITerm Z] $net
    foreach pg {VDD VSS} {
        set term [$orig findITerm $pg]
        if {$term ne "NULL" && [$term getNet] ne "NULL"} {
            odb::dbITerm_connect [$instance findITerm $pg] [$term getNet]
        }
    }
    set wire [$net getWire]
    if {$wire ne "NULL"} { odb::dbWire_destroy $wire }
    lappend affected $name eco_feed_$serial
    set_load -pin_load $load [get_ports [list $name]]
    incr serial
}
puts "Inserted $serial BUF_X$strength output drivers"
set_thread_count $::env(SLURM_CPUS_PER_TASK)
detailed_placement -max_displacement {650 500}
check_placement -verbose
write_db eco-placed.odb
write_def eco-placed.def
write_verilog eco-placed.v
set_routing_layers -signal metal1-metal10
set_nets_to_route $affected
global_route -allow_congestion -congestion_iterations 8 -guide_file eco.guide
write_db eco-global.odb
detailed_route -droute_end_iter 12 -output_drc eco-drc.rpt -via_in_pin_bottom_layer metal10 -via_in_pin_top_layer metal10
filler_placement {FILLCELL_X32 FILLCELL_X16 FILLCELL_X8 FILLCELL_X4 FILLCELL_X2 FILLCELL_X1}
global_connect
write_db eco-routed.odb
write_def eco-routed.def
write_verilog eco-routed.v
