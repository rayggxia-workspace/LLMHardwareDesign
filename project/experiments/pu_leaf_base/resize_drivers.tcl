# Resize standard-cell drivers implicated by the final extracted audit.
set block [ord::get_db_block]
set db [ord::get_db]
set drivers [dict create]
foreach endpoint $pu_resize_pins {
    set split [string last / $endpoint]
    set inst [$block findInst [string range $endpoint 0 $split-1]]
    if {$inst eq "NULL"} {error "audit instance missing from checkpoint: $endpoint"}
    set pin [$inst findITerm [string range $endpoint $split+1 end]]
    if {$pin eq "NULL" || [$pin getNet] eq "NULL"} {error "invalid electrical pin $endpoint"}
    set net [$pin getNet]
    if {[$net getSigType] in {CLOCK POWER GROUND}} {continue}
    foreach term [$net getITerms] {
        if {[[$term getMTerm] getIoType] ne "OUTPUT"} {continue}
        set driver [$term getInst]
        if {[[$driver getMaster] isBlock]} {continue}
        dict set drivers [$driver getName] $driver
    }
}
set changed 0
dict for {name inst} $drivers {
    set old [[$inst getMaster] getName]
    if {![regexp {^(.+)_X(1|2|4|8|16)$} $old -> family drive]} {continue}
    foreach size {8 4 2 16 32} {
        if {$size < 4*$drive} {continue}
        set candidate ${family}_X$size
        if {[$db findMaster $candidate] eq "NULL"} {continue}
        replace_cell $name $candidate
        if {[[$inst getMaster] getName] ne $candidate} {error "replacement failed for $name"}
        puts "PU_DRIVER_RESIZE $name $old $candidate"
        incr changed
        break
    }
}
if {$changed == 0} {error "no electrical drivers could be resized"}
detailed_placement
check_placement -verbose
