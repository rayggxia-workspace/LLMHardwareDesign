read_db $::env(CFJ_FINAL_ODB)
set block [ord::get_db_block]
set f [open $::env(CFJ_ENDPOINTS) w]
foreach term [$block getBTerms] {
    if {![string match "late_*" [$term getName]]} {continue}
    set net [$term getNet]
    if {$net eq "NULL"} {error "missing native net for [$term getName]"}
    foreach pin [$term getBPins] {
        foreach box [$pin getBoxes] {
            if {[[$box getTechLayer] getName] ne "metal10"} {continue}
            puts $f [join [list [$term getName] [$term getIoType] [$net getName] [$box xMin] [$box yMin] [$box xMax] [$box yMax]] "\t"]
        }
    }
}
close $f
