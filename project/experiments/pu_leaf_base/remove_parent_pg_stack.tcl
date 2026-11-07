# Remove diagnosed redundant parent M7-M10 PG stacks, leaving all stripes intact.
set handle [open $::env(PU_FINAL_PG_REMOVAL) r]
while {[gets $handle line] >= 0} {
    if {![regexp {^(VDD|VSS) ([0-9]+) ([0-9]+)$} $line -> supply x y]} {
        error "invalid parent PG stack selection: $line"
    }
    set stack {}
    set kinds {}
    foreach swire [[$block findNet $supply] getSWires] {
        foreach shape [$swire getWires] {
            if {![$shape isVia] || [$shape getViaXY] ne [list $x $y]} {continue}
            set via [$shape getBlockVia]
            if {$via eq "NULL"} {set via [$shape getTechVia]}
            set levels {}
            foreach box [$via getBoxes] {
                set number [[$box getTechLayer] getRoutingLevel]
                if {$number} {lappend levels $number}
            }
            lappend kinds [lsort -integer -unique $levels]
            lappend stack $shape
        }
    }
    if {[lsort $kinds] ne {{7 8} {8 9} {9 10}}} {error "unexpected parent PG stack at $line"}
    foreach shape $stack {odb::dbSBox_destroy $shape}
    puts "PU_REDUNDANT_PARENT_PG_STACK_REMOVED $line"
}
close $handle
foreach supply {VDD VSS} {
    if {[check_power_grid -net $supply] ne "1"} {error "PG stack removal disconnects $supply"}
}
