read_db $::env(START_ODB)
set block [ord::get_db_block]
set layer [[ord::get_db_tech] findLayer metal3]
set encoder [odb::dbWireEncoder]
set tsv [open $::env(LANDING_PATCHES) r]
while {[gets $tsv line] >= 0} {
    lassign [split $line "\t"] inst pin expected a b c d
    set bank [$block findInst $inst]
    if {$bank eq "NULL" || [$bank getOrient] ne "R0"} { error "Invalid SRAM placement $inst" }
    set term [$bank findITerm $pin]
    set net [$term getNet]
    if {[$net getName] ne $expected} { error "Landing net changed for $inst $pin" }
    set wire [$net getWire]
    if {$wire eq "NULL"} { error "Missing native route for $expected" }
    set x [expr {($a+$c)/2}]
    set y [expr {($b+$d)/2}]
    $encoder append $wire
    $encoder newPath $layer ROUTED
    $encoder addPoint $x $y
    $encoder addRect [expr {$a-$x}] [expr {$b-$y}] [expr {$c-$x}] [expr {$d-$y}]
    $encoder addITerm $term
    $encoder end
    puts "Restored accepted M3 landing $inst $pin on $expected"
}
close $tsv
if {![design_is_routed]} { error "Patched design is not routed" }
check_antennas -report_file antenna.rpt
write_db eco-routed.odb
write_def eco-routed.def
write_verilog eco-routed.v
