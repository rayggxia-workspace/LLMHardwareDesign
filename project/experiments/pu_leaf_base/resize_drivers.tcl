# Resize standard-cell drivers implicated by the final extracted audit.
set block [ord::get_db_block]
set db [ord::get_db]
set drivers [dict create]
set receiver_branches [dict create]
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
        if {[[$pin getMTerm] getIoType] eq "INPUT" && [[$inst getMaster] isBlock]} {
            set driver_master [[$driver getMaster] getName]
            if {[[$driver getMaster] isBlock] ||
                ([regexp {_X(16|32)$} $driver_master])} {
                dict set receiver_branches $endpoint $pin
            }
        }
        if {[[$driver getMaster] isBlock]} {continue}
        dict set drivers [$driver getName] $driver
    }
}
set changed 0
dict for {name inst} $drivers {
    set old [[$inst getMaster] getName]
    if {![regexp {^(.+)_X(1|2|4|8|16)$} $old -> family drive]} {continue}
    foreach size {8 4 16 32 2} {
        if {$size <= $drive} {continue}
        set candidate ${family}_X$size
        if {[$db findMaster $candidate] eq "NULL"} {continue}
        replace_cell $name $candidate
        if {[[$inst getMaster] getName] ne $candidate} {error "replacement failed for $name"}
        puts "PU_DRIVER_RESIZE $name $old $candidate"
        incr changed
        break
    }
}
dict for {endpoint sink} $receiver_branches {
    set inst [$sink getInst]
    if {[$inst getOrient] ne "R0"} {error "receiver repair requires verified R0 geometry: $endpoint"}
    set net [$sink getNet]
    if {$net eq "NULL" || [$net getSigType] ne "SIGNAL"} {error "invalid receiver branch: $endpoint"}
    set landing ""
    foreach mpin [[$sink getMTerm] getMPins] {
        foreach box [$mpin getGeometry] {
            if {[[$box getTechLayer] getName] eq "metal10"} {set landing $box; break}
        }
        if {$landing ne ""} {break}
    }
    if {$landing eq ""} {error "receiver has no verified M10 landing: $endpoint"}
    lassign [$inst getLocation] dx dy
    set px [expr {$dx+([$landing xMin]+[$landing xMax])/2}]
    set py [expr {$dy+([$landing yMin]+[$landing yMax])/2}]
    set master [$db findMaster BUF_X8]
    if {$master eq "NULL"} {error "BUF_X8 is required for receiver repair"}
    set bounds [$inst getBBox]
    set w [$master getWidth];set h [$master getHeight]
    set choices [list \
        [list [expr {abs($px-[$bounds xMin])}] [expr {[$bounds xMin]-4000-$w}] [expr {$py-$h/2}]] \
        [list [expr {abs($px-[$bounds xMax])}] [expr {[$bounds xMax]+4000}] [expr {$py-$h/2}]] \
        [list [expr {abs($py-[$bounds yMin])}] [expr {$px-$w/2}] [expr {[$bounds yMin]-4000-$h}]] \
        [list [expr {abs($py-[$bounds yMax])}] [expr {$px-$w/2}] [expr {[$bounds yMax]+4000}]]]
    lassign [lindex [lsort -real -index 0 $choices] 0] distance x y
    set index 0
    while {[$block findInst pu_receiver_buffer_$index] ne "NULL" ||
           [$block findNet pu_receiver_buffer_${index}_Z] ne "NULL"} {incr index}
    set name pu_receiver_buffer_$index
    set buffer [odb::dbInst_create $block $master $name]
    set next [odb::dbNet_create $block ${name}_Z]
    $buffer setLocation $x $y
    $buffer setOrient R0
    $buffer setPlacementStatus PLACED
    [$buffer findITerm A] connect $net
    [$buffer findITerm Z] connect $next
    $sink disconnect
    $sink connect $next
    set_dont_touch [get_cells $name]
    puts "PU_RECEIVER_BUFFER $endpoint $name $x $y"
    incr changed
}
if {$changed == 0} {error "no electrical drivers could be resized or buffered"}
global_connect
detailed_placement
check_placement -verbose
