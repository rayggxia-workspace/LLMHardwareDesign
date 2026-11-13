set_thread_count $::env(SLURM_CPUS_PER_TASK)
set args [split $::env(JOINT_ODB_AUDIT_INPUT) "|"]
lassign $args db rows out require_wires
read_db $db
set block [ord::get_db_block]
set f [open $rows r]
set report [open $out w]
set parent 0
set leaf 0
set routed 0
while {[gets $f line] >= 0} {
    lassign [split $line "\t"] kind term name role shapes
    set net [$block findNet $name]
    if {$net eq "NULL"} {error "Missing OpenDB net $name"}
    set observed {}
    if {$kind eq "parent_escape_required"} {
        set bterm [$block findBTerm $term]
        if {$bterm eq "NULL" || [$bterm getNet] ne $net} {error "Wrong BTerm owner $term"}
        set direction [expr {$role eq "driver" ? "OUTPUT" : "INPUT"}]
        if {[$bterm getIoType] ne $direction} {error "Wrong BTerm direction $term"}
        foreach pin [$bterm getBPins] {
            foreach box [$pin getBoxes] {
                if {[[$box getTechLayer] getRoutingLevel] == 10} {
                    lappend observed [list [$box xMin] [$box yMin] [$box xMax] [$box yMax]]
                }
            }
        }
        incr parent
        if {[$net getWire] ne "NULL"} {incr routed} elseif {$require_wires} {error "Missing lower wire $term"}
    } else {
        set idx [string last / $term]
        set inst [$block findInst [string range $term 0 [expr {$idx-1}]]]
        if {$inst eq "NULL"} {error "Missing leaf instance $term"}
        set iterm [$inst findITerm [string range $term [expr {$idx+1}] end]]
        if {$iterm eq "NULL" || [$iterm getNet] ne $net} {error "Wrong ITerm owner $term"}
        set mterm [$iterm getMTerm]
        set direction [expr {$role eq "driver" ? "OUTPUT" : "INPUT"}]
        if {[$mterm getIoType] ne $direction} {error "Wrong ITerm direction $term"}
        if {[$inst getOrient] ne "R0" || [[$inst getMaster] getOrigin] ne {0 0}} {
            error "Unsupported leaf transform $term"
        }
        lassign [$inst getLocation] ox oy
        foreach pin [$mterm getMPins] {
            foreach box [$pin getGeometry] {
                if {[[$box getTechLayer] getRoutingLevel] == 10} {
                    lappend observed [list [expr {$ox+[$box xMin]}] [expr {$oy+[$box yMin]}] \
                        [expr {$ox+[$box xMax]}] [expr {$oy+[$box yMax]}]]
                }
            }
        }
        incr leaf
    }
    if {[lsort -unique $observed] ne [lsort -unique $shapes]} {error "OpenDB geometry differs on $term"}
}
puts $report "parent_bterms\t$parent"
puts $report "native_iterms\t$leaf"
puts $report "lower_routed_parent_bterms\t$routed"
close $report
close $f
