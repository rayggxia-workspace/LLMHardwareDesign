# Reduce the measured SRAM output load without changing its logic or capacity.
set block [ord::get_db_block]
set escape [list [format %c 91] [format %c%c 92 91] [format %c 93] [format %c%c 92 93]]
set getter [expr {[llength [info commands odb::dbInst_isDoNotTouch]] ? "isDoNotTouch" : "getDoNotTouch"}]
foreach entry $ucf_receiver_targets {
    lassign $entry bank_name pin_name
    set bank [$block findInst $bank_name]
    if {$bank eq "NULL"} {set bank [$block findInst [string map $escape $bank_name]]}
    if {$bank eq "NULL" || [[$bank getMaster] getName] ne "s_sram_256x128_freepdk45"} {
        error "Measured SRAM instance is missing"
    }
    set driver [$bank findITerm $pin_name]
    if {$driver eq "NULL" || [$driver getIoType] ne "OUTPUT"} {error "Missing SRAM output"}
    set net [$driver getNet]
    if {$net eq "NULL" || [llength [$net getITerms]] != 2 || [llength [$net getBTerms]] != 0} {
        error "Expected exactly one receiver on the measured SRAM output"
    }
    set sink [lindex [lsearch -all -inline -not -exact [$net getITerms] $driver] 0]
    set inst [$sink getInst]
    set old_master [$inst getMaster]
    set new_master [[ord::get_db] findMaster CLKBUF_X1]
    if {[[$sink getMTerm] getName] ne "A" || [$old_master getName] ne "BUF_X1" ||
        $new_master eq "NULL" || [$old_master getWidth] != [$new_master getWidth] ||
        [$old_master getHeight] != [$new_master getHeight]} {
        error "Unexpected receiver cell or footprint at $bank_name/$pin_name"
    }
    set inst_name [$inst getName]
    set pos [$inst getLocation]
    set orient [$inst getOrient]
    set saved {}
    foreach term [$inst getITerms] {
        set term_net [$term getNet]
        if {$term_net eq "NULL"} {error "A receiver pin is unconnected"}
        dict set saved [[$term getMTerm] getName] [list $term_net [$term_net getWire]]
    }
    set protected [$inst $getter]
    $inst setDoNotTouch false
    set cells [get_cells [list $inst_name]]
    if {[llength $cells] != 1 || [replace_cell $cells CLKBUF_X1] != 1} {
        error "Measured receiver replacement failed"
    }
    set inst [$block findInst $inst_name]
    $inst setDoNotTouch $protected
    if {[$inst getMaster] ne $new_master || [$inst getLocation] ne $pos ||
        [$inst getOrient] ne $orient || [llength [$inst getITerms]] != [dict size $saved]} {
        error "Replacement altered receiver placement, orientation, or pin count"
    }
    dict for {pin data} $saved {
        lassign $data old_net old_wire
        set iterm [$inst findITerm $pin]
        if {$iterm eq "NULL" || [$iterm getNet] ne $old_net || [$old_net getWire] ne $old_wire} {
            error "Replacement altered receiver connectivity or cleared an existing wire"
        }
    }
    if {[$driver getNet] ne $net || [llength [$net getITerms]] != 2} {
        error "SRAM output fanout was changed"
    }
    puts "UCF_LOW_CAP_RECEIVER $bank_name/$pin_name -> $inst_name BUF_X1-to-CLKBUF_X1 at $pos"
}
check_placement -verbose
