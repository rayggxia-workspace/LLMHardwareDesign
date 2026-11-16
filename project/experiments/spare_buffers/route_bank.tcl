# Make one independently verifiable four-buffer bank using Nangate45.
set p $::env(PLATFORM_DIR)
set_thread_count 4
read_lef $p/lef/NangateOpenCellLibrary.tech.lef
read_lef $p/lef/NangateOpenCellLibrary.macro.mod.lef
read_liberty $p/lib/NangateOpenCellLibrary_typical.lib
read_verilog bank.v
link_design spare_bank
set site FreePDK45_38x28_10R_NP_162NW_34O
initialize_floorplan -die_area {0 0 48 56} -core_area {2 2.8 46 53.2} -site $site
source $p/make_tracks.tcl
foreach {name x y} {b0 10.07 8.4 b1 28.12 19.6 b2 10.07 30.8 b3 28.12 42.0} {
    place_inst -name $name -location [list $x $y] -orient R0 -status FIRM
}
check_placement -verbose
foreach {supply kind} {VDD power VSS ground} {
    add_global_connection -net $supply -inst_pattern {^b[0-3]$} -pin_pattern ^${supply}$ -$kind
}
global_connect
set_voltage_domain -name CORE -power VDD -ground VSS
define_pdn_grid -name grid -voltage_domains CORE -pins metal10
add_pdn_stripe -grid grid -layer metal1 -width 0.17 -pitch 2.8 -offset 0 -followpins
add_pdn_stripe -grid grid -layer metal4 -width 0.48 -pitch 16 -offset 2
add_pdn_stripe -grid grid -layer metal7 -width 1.4 -pitch 16 -offset 2
add_pdn_stripe -grid grid -layer metal10 -width 1.6 -pitch 24 -offset 2
add_pdn_connect -grid grid -layers {metal1 metal4}
add_pdn_connect -grid grid -layers {metal4 metal7}
add_pdn_connect -grid grid -layers {metal7 metal10}
pdngen
foreach supply {VDD VSS} {
    if {[check_power_grid -net $supply -dont_require_terminals] ne "1"} {error "Disconnected $supply"}
}
set block [ord::get_db_block]
set metal10 [[ord::get_db_tech] findLayer metal10]
set dbu [$block getDbUnitsPerMicron]
set rails {}
set ports [open bank-ports.tsv w]
puts $ports "instance\tpin\tx_dbu\ty_dbu\tx0_dbu\ty0_dbu\tx1_dbu\ty1_dbu\tanchor_x_dbu\tanchor_y_dbu"
foreach supply {VDD VSS} {
    foreach term [[$block findNet $supply] getBTerms] {
        foreach port [$term getBPins] {
            foreach box [$port getBoxes] {
                if {[$box getTechLayer] ne $metal10} {continue}
                lappend rails [list [$box xMin] [$box xMax]]
                puts $ports [join [list PG $supply [expr {([$box xMin]+[$box xMax])/2}] [expr {([$box yMin]+[$box yMax])/2}] [$box xMin] [$box yMin] [$box xMax] [$box yMax] - -] \t]
            }
        }
    }
}
if {[llength $rails] < 2} {error "Missing M10 power terminals"}
set reserved {}
set cells [open bank-cells.tsv w]
puts $cells "instance\tx_dbu\ty_dbu\twidth_dbu\theight_dbu"
set centres [expr {round(1.6*$dbu)}]
set offset [expr {round(0.095*$dbu)}]
set spacing [expr {round(4.2*$dbu)}]
foreach name {b0 b1 b2 b3} {
    set instance [$block findInst $name]
    set master [$instance getMaster]
    lassign [$instance getOrigin] ix iy
    puts $cells [join [list $name $ix $iy [$master getWidth] [$master getHeight]] \t]
    foreach pin {A Z} {
        set t [$instance findITerm $pin]
        set rect [$t getBBox]
        set ax [expr {([$rect xMin]+[$rect xMax])/2}]
        # The first pin rectangle contains a real horizontal stripe.
        set shape [lindex [[lindex [[$t getMTerm] getMPins] 0] getGeometry] 0]
        set anchor_x [expr {$ix+([$shape xMin]+[$shape xMax])/2}]
        set anchor_y [expr {$iy+([$shape yMin]+[$shape yMax])/2}]
        # Match the PR271 fine upper-access lattice, origin 0.095/0.070 um.
        set pin_y [expr {([$rect yMax]+[$rect yMin])/2.0/$dbu}]
        set y [expr {round(($pin_y-0.07)/0.2)*0.2+0.07}]
        set candidates {}
        for {set x $offset} {$x < 46*$dbu} {incr x $centres} {
            if {$x < 2*$dbu} {continue}
            set available 1
            foreach rail $rails {
                lassign $rail lo hi
                if {$x+$dbu*1.8 > $lo && $x-$dbu*1.8 < $hi} {set available 0; break}
            }
            foreach xy $reserved {
                lassign $xy other_x other_y
                if {abs($x-$other_x) < $spacing && abs($y-$other_y) < 4.2} {set available 0; break}
            }
            if {$available} {lappend candidates [list [expr {abs($x-$ax)}] $x]}
        }
        if {![llength $candidates]} {error "No M10 candidate for $name/$pin"}
        set x [lindex [lsort -integer -index 0 $candidates] $::env(PIN_RANK) 1]
        if {$x eq ""} {error "No M10 candidate at rank $::env(PIN_RANK) for $name/$pin"}
        lappend reserved [list $x $y]
        place_pin -pin_name ${name}_$pin -layer metal10 -location [list [expr {double($x)/$dbu}] $y] -pin_size {2.0 2.0}
        set bterm [$block findBTerm ${name}_$pin]
        set box [lindex [[lindex [$bterm getBPins] 0] getBoxes] 0]
        puts $ports [join [list $name $pin [expr {([$box xMin]+[$box xMax])/2}] [expr {([$box yMin]+[$box yMax])/2}] [$box xMin] [$box yMin] [$box xMax] [$box yMax] $anchor_x $anchor_y] \t]
    }
}
close $cells
close $ports
set_routing_layers -signal metal2-metal10
global_route -guide_file bank.guide
detailed_route -output_drc bank-router.drc -droute_end_iter 32
foreach n [$block getNets] {
    if {[llength [$n getBTerms]] && [$n getSigType] ni {POWER GROUND} && [$n getWire] eq "NULL"} {
        error "Unrouted net [$n getName]"
    }
}
if {![design_is_routed -verbose]} {error "Unrouted bank"}
if {[file size bank-router.drc] != 0} {error "Detailed router reports violations"}
write_db bank.odb
write_def bank.def
puts BANK_ROUTE_OK
