# A scratch ODB moves only measured physical-only row-end taps. Native
# signal cells and routed wires retain the selected physical candidate.
read_db $::env(CFJ_WELL_SOURCE)
set block [ord::get_db_block]
set edits [open $::env(CFJ_WELL_EDITS) r]
remove_fillers
while {[gets $edits line] >= 0} {
    lassign [split $line "\t"] name side
    set inst [$block findInst $name]
    if {$inst eq "NULL" || [[$inst getMaster] getName] ne "TAPCELL_X1"} {
        error "missing qualified row-end tap $name"
    }
    foreach pin [$inst getITerms] {
        if {[[$pin getMTerm] getSigType] ni {POWER GROUND}} {
            error "unexpected signal on physical-only tap $name"
        }
    }
    lassign [$inst getLocation] x y
    set status [$inst getPlacementStatus]
    set delta [expr {380 * $::env(CFJ_WELL_SITES) * $side}]
    $inst setPlacementStatus PLACED
    $inst setLocation [expr {$x+$delta}] $y
    $inst setPlacementStatus $status
    puts "CFJ_TAP $name $x $y [expr {$x+$delta}] $y"
}
close $edits
filler_placement {FILLCELL_X1 FILLCELL_X2 FILLCELL_X4 FILLCELL_X8 FILLCELL_X16 FILLCELL_X32}
global_connect
check_placement -verbose
foreach net {VDD VSS} {
    if {[check_power_grid -net $net] ne "1"} {error "incomplete $net after row-end tap move"}
}
write_db $::env(CFJ_WELL_TARGET)
