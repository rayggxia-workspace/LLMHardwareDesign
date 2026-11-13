set_thread_count $::env(SLURM_CPUS_PER_TASK)
lassign [split $::env(DMA_PIN_INPUT) "|"] database manifest report
read_db $database
set block [ord::get_db_block]
set fin [open $manifest r]
set fout [open $report w]
puts $fout "family\tlogical_pin\tdirection\tnative_net\tplaced_bpin_shapes"
while {[gets $fin row] >= 0} {
    lassign [split $row "\t"] family name direction
    set port [$block findBTerm $name]
    if {$port eq "NULL" || [$port getIoType] ne $direction} {
        error "missing or wrong direction DMA port $name"
    }
    set shapes {}
    foreach pin [$port getBPins] {
        foreach box [$pin getBoxes] {
            set layer [$box getTechLayer]
            lappend shapes [list [$layer getName] [$layer getRoutingLevel] \
                [$box xMin] [$box yMin] [$box xMax] [$box yMax]]
        }
    }
    puts $fout [join [list $family $name $direction [[$port getNet] getName] $shapes] "\t"]
}
close $fout
close $fin
