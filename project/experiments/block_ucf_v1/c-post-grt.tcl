# Exact logic-preserving edits at the end of the existing C16 global route.
proc ucf_eco_find {block instance pin} {
    set esc [list [format %c 91] [format %c%c 92 91] [format %c 93] [format %c%c 92 93]]
    set inst [$block findInst $instance]
    if {$inst eq "NULL"} {set inst [$block findInst [string map $esc $instance]]}
    if {$inst eq "NULL"} {error "Missing measured instance $instance"}
    set term [$inst findITerm $pin]
    if {$term eq "NULL"} {set term [$inst findITerm [string map $esc $pin]]}
    if {$term eq "NULL"} {error "Missing measured pin $instance/$pin"}
    return [list $inst $term]
}

proc ucf_eco_buffer {block name master x y} {
    if {[$block findInst $name] ne "NULL" || [$block findNet ${name}_net] ne "NULL"} {
        error "Unexpected duplicate ECO cell"
    }
    set lib [[ord::get_db] findMaster $master]
    if {$lib eq "NULL" || $master ni {BUF_X1 BUF_X2}} {error "Unknown ECO buffer"}
    set inst [odb::dbInst_create $block $lib $name]
    $inst setOrient R0
    $inst setLocation $x $y
    $inst setPlacementStatus PLACED
    foreach {port sig} {VDD POWER VSS GROUND} {
        set term [$inst findITerm $port]
        set net [$block findNet $port]
        if {$term eq "NULL" || $net eq "NULL" || [$term getSigType] ne $sig || [$net getSigType] ne $sig} {
            error "Cannot supply $name/$port"
        }
        $term connect $net
        if {[$term getNet] ne $net} {error "ECO PG connection mismatch"}
    }
    return $inst
}

proc ucf_eco_unlocked_reconnect {term from to} {
    set inst [$term getInst]
    set getter [expr {[llength [info commands odb::dbInst_isDoNotTouch]] ? "isDoNotTouch" : "getDoNotTouch"}]
    set protected [$inst $getter]
    if {[$term getNet] ne $from} {error "Unexpected ECO terminal source"}
    $inst setDoNotTouch false
    try {
        $term disconnect
        $term connect $to
    } finally {
        $inst setDoNotTouch $protected
    }
    if {[$term getNet] ne $to} {error "ECO terminal reconnection failed"}
}

set block [ord::get_db_block]
global_route -start_incremental
set index 0
foreach entry $ucf_eco_hold {
    lassign $entry instance pin stages
    lassign [ucf_eco_find $block $instance $pin] inst term
    if {[$term getIoType] ne "INPUT" || $pin ne "D" || [[$inst getMaster] getName] ni {DFF_X1 DFF_X2}} {
        error "Unrecognized measured C16 hold target $instance/$pin"
    }
    set old [$term getNet]
    if {$old eq "NULL" || [$old getSigType] ne "SIGNAL" || [llength [$old getBTerms]]} {
        error "Hold target lacks an internal data net"
    }
    set saved [dict create]
    foreach iterm [$inst getITerms] {
        if {$iterm ne $term} {dict set saved $iterm [$iterm getNet]}
    }
    lassign [$inst getLocation] x y
    set previous $old
    for {set i 0} {$i < $stages} {incr i} {
        set name ucf_eco_hold_${index}_$i
        set buf [ucf_eco_buffer $block $name BUF_X1 [expr {$x+4000+4000*$i}] $y]
        set next [odb::dbNet_create $block ${name}_net]
        [$buf findITerm A] connect $previous
        [$buf findITerm Z] connect $next
        set previous $next
    }
    ucf_eco_unlocked_reconnect $term $old $previous
    dict for {iterm net} $saved {
        if {[$iterm getNet] ne $net} {error "ECO changed an unrelated hold-target pin"}
    }
    puts "UCF_POST_ECO_HOLD $instance/$pin stages=$stages"
    incr index
}
set index 0
foreach entry $ucf_eco_cap {
    lassign $entry instance pin
    lassign [ucf_eco_find $block $instance $pin] inst term
    set net [$term getNet]
    if {$net eq "NULL" || [$term getIoType] ne "OUTPUT" || [$net getSigType] ne "SIGNAL"} {
        error "Invalid measured C16 capacitance driver $instance/$pin"
    }
    set master [[$inst getMaster] getName]
    if {$master eq "OAI21_X1" && $pin eq "ZN"} {
        set cells [get_cells [list $instance]]
        if {[llength $cells] != 1 || [replace_cell $cells OAI21_X2] != 1} {
            error "C16 measured drive replacement failed"
        }
        lassign [ucf_eco_find $block $instance $pin] inst term
        if {[[$inst getMaster] getName] ne "OAI21_X2" || [$term getNet] ne $net} {
            error "C16 drive replacement changed connectivity"
        }
        puts "UCF_POST_ECO_CAP $instance/$pin OAI21_X1->OAI21_X2"
    } elseif {$master eq "s_sram_256x128_freepdk45" && [regexp {^dout0\[[0-9]+\]$} $pin]} {
        set loads [$net getITerms]
        if {[llength $loads] != 2 || [llength [$net getBTerms]] != 0} {error "Unexpected SRAM output fanout"}
        set load [lindex [lsearch -all -inline -not -exact $loads $term] 0]
        if {[$load getIoType] ne "INPUT"} {error "Unexpected SRAM load pin direction"}
        # Real transformed pin coordinates and the bank outline determine the
        # closest exterior insertion site; no change to the hard SRAM master.
        set p [$term getBBox]
        set box [$inst getBBox]
        set x [expr {([$p xMin]+[$p xMax])/2}]
        set y [expr {([$p yMin]+[$p yMax])/2}]
        set gap [expr {[$block getDbUnitsPerMicron] * $ucf_eco_variant}]
        set lib [[ord::get_db] findMaster BUF_X1]
        set choices [list [list [expr {abs($x-[$box xMin])}] [expr {[$box xMin]-$gap-[$lib getWidth]}] $y] \
            [list [expr {abs($x-[$box xMax])}] [expr {[$box xMax]+$gap}] $y] \
            [list [expr {abs($y-[$box yMin])}] $x [expr {[$box yMin]-$gap-[$lib getHeight]}]] \
            [list [expr {abs($y-[$box yMax])}] $x [expr {[$box yMax]+$gap}]]]
        lassign [lindex [lsort -integer -index 0 $choices] 0] distance x y
        set name ucf_eco_bank_$index
        set buf [ucf_eco_buffer $block $name BUF_X1 $x $y]
        set short [odb::dbNet_create $block ${name}_net]
        set net_getter [expr {[llength [info commands odb::dbNet_isDoNotTouch]] ? "isDoNotTouch" : "getDoNotTouch"}]
        set protected [$net $net_getter]
        $net setDoNotTouch false
        try {
            ucf_eco_unlocked_reconnect $term $net $short
            [$buf findITerm A] connect $short
            [$buf findITerm Z] connect $net
        } finally {
            $net setDoNotTouch $protected
        }
        $short setDoNotTouch $protected
        if {[$net $net_getter] ne $protected || [$short $net_getter] ne $protected} {
            error "SRAM edge protection was not restored"
        }
        if {[$load getNet] ne $net || [llength [$short getITerms]] != 2 || [llength [$net getITerms]] != 2} {
            error "SRAM driver isolation changed output fanout"
        }
        puts "UCF_POST_ECO_CAP $instance/$pin BUF_X1 at $x,$y nearest edge distance $distance"
    } else {
        error "Measured C16 cap driver $instance/$pin uses unsupported master $master"
    }
    incr index
}
global_connect
detailed_placement_helper
check_placement -verbose
global_route -end_incremental
write_guides $::env(RESULTS_DIR)/route.guide
puts "UCF_POST_ECO_COMPLETE C16 measured hold/cap ECO"
