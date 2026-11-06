read_db $::env(CFJ_FINAL_ODB)
set block [ord::get_db_block]
set unit [open "$::env(CFJ_ENDPOINTS).dbu" w]
puts $unit [$block getDbUnitsPerMicron]
close $unit
set f [open $::env(CFJ_ENDPOINTS) w]
foreach term [$block getBTerms] {
    if {![string match "late_*" [$term getName]]} {continue}
    set net [$term getNet]
    if {$net eq "NULL"} {error "missing native net for [$term getName]"}
    set drivers {}
    set loads {}
    foreach iterm [$net getITerms] {
        set name "[[$iterm getInst] getName]/[[$iterm getMTerm] getName]"
        if {[[$iterm getMTerm] getIoType] eq "OUTPUT"} {
            lappend drivers $name
        } elseif {[[$iterm getMTerm] getIoType] eq "INPUT"} {
            lappend loads $name
        }
    }
    if {([$term getIoType] eq "OUTPUT" && [llength $drivers] != 1) ||
        ([$term getIoType] eq "INPUT" && ([llength $drivers] != 0 || [llength $loads] == 0))} {
        error "invalid routed native ownership on [$term getName]"
    }
    foreach pin [$term getBPins] {
        foreach box [$pin getBoxes] {
            if {[[$box getTechLayer] getName] ne "metal10"} {continue}
            puts $f [join [list [$term getName] [$term getIoType] [$net getName] [$box xMin] [$box yMin] [$box xMax] [$box yMax]] "\t"]
        }
    }
}
close $f
