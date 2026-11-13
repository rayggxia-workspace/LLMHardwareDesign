set_thread_count $::env(SLURM_CPUS_PER_TASK)
lassign [split $::env(JOINT_MAIN_P_INPUT) "|"] db requests out
read_db $db
set block [ord::get_db_block]
set f [open $requests r]
set report [open $out w]
puts $report "family\tlogical_pin\tdirection\tnative_net\tboundary_rects\tleaf_shapes"
while {[gets $f line] >= 0} {
    lassign [split $line "\t"] family pin direction
    set bterm [$block findBTerm $pin]
    if {$bterm eq "NULL" || [$bterm getIoType] ne $direction} {error "Missing or wrong-direction port $pin"}
    set net [$bterm getNet]
    set boundaries {}
    foreach bp [$bterm getBPins] {
        foreach box [$bp getBoxes] {
            if {[[$box getTechLayer] getRoutingLevel] == 10} {
                lappend boundaries [list [$box xMin] [$box yMin] [$box xMax] [$box yMax]]
            }
        }
    }
    set leaves {}
    foreach iterm [$net getITerms] {
        set inst [$iterm getInst]
        set master [$inst getMaster]
        set mterm [$iterm getMTerm]
        if {[$master getType] ne "BLOCK" || [$mterm getIoType] ne $direction} {continue}
        if {[$inst getOrient] ne "R0" || [$master getOrigin] ne {0 0}} {
            error "Unknown macro orientation $pin/[$inst getName]"
        }
        lassign [$inst getLocation] ox oy
        foreach mpin [$mterm getMPins] {
            foreach box [$mpin getGeometry] {
                if {[[$box getTechLayer] getRoutingLevel] == 10} {
                    lappend leaves [list [$inst getName] [$mterm getName] \
                        [expr {$ox+[$box xMin]}] [expr {$oy+[$box yMin]}] \
                        [expr {$ox+[$box xMax]}] [expr {$oy+[$box yMax]}]]
                }
            }
        }
    }
    puts $report [join [list $family $pin $direction [$net getName] $boundaries $leaves] "\t"]
}
close $report
close $f
