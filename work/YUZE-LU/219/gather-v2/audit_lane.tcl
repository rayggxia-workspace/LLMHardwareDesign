set_thread_count $::env(SLURM_CPUS_PER_TASK)
read_db $::env(DMA_ODB)
set block [ord::get_db_block]
set fin [open $::env(DMA_MANIFEST) r]
set result [open $::env(DMA_AUDIT) w]
puts $result "family\tlogical_pin\tdirection\tnative_net\tplaced_bpin_shapes\tinternal_terms\tboundary_terms"
while {[gets $fin row] >= 0} {
    lassign [split $row "\t"] family name direction
    set port [$block findBTerm $name]
    if {$port eq "NULL" || [$port getIoType] ne $direction} {
        error "source DMA port missing or wrong direction: $name"
    }
    set net [$port getNet]
    if {$net eq "NULL"} {
        error "port lacks net: $name"
    }
    set shapes {}
    foreach pin [$port getBPins] {
        foreach box [$pin getBoxes] {
            set layer [$box getTechLayer]
            lappend shapes [list [$layer getName] [$layer getRoutingLevel] \
                [$box xMin] [$box yMin] [$box xMax] [$box yMax]]
        }
    }
    puts $result [join [list $family $name $direction [$net getName] $shapes \
        [llength [$net getITerms]] [llength [$net getBTerms]]] "\t"]
}
close $fin
close $result
