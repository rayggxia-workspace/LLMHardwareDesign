set_thread_count $::env(SLURM_CPUS_PER_TASK)
read_db $::env(NATIVE_DMA_ODB)
set block [ord::get_db_block]
set metal10 [[[ord::get_db] getTech] findLayer metal10]
set rows [open $::env(NATIVE_DMA_LANDINGS) r]
set ports 0
while {[gets $rows line] >= 0} {
    lassign [split $line "\t"] name direction x0 y0 x1 y1
    set port [$block findBTerm $name]
    if {$port eq "NULL" || [$port getIoType] ne $direction || [llength [$port getBPins]] != 1} {
        error "unexpected physical interface on $name"
    }
    set net [$port getNet]
    if {[llength [$net getITerms]] == 0 || [$net getWire] ne "NULL"} {
        error "DMA input must be placed and unrouted at $name"
    }
    odb::dbBPin_destroy [lindex [$port getBPins] 0]
    set new [odb::dbBPin_create $port]
    $new setPlacementStatus FIRM
    odb::dbBox_create $new $metal10 $x0 $y0 $x1 $y1
    incr ports
}
close $rows
if {$ports != 4344} {error "incomplete DMA port migration"}
set_routing_layers -signal metal2-metal10 -clock metal4-metal10
set out $::env(NATIVE_DMA_OUTPUT)
global_route -guide_file "$out/route.guide" -congestion_report_file "$out/congestion.rpt" -allow_congestion
set rows [open $::env(NATIVE_DMA_LANDINGS) r]
set missing 0
while {[gets $rows line] >= 0} {
    set name [lindex [split $line "\t"] 0]
    set net [[$block findBTerm $name] getNet]
    if {![llength [$net getGuides]]} {incr missing}
}
close $rows
puts "DMA_M10_GLOBAL_ROUTE staged=$ports missing_guide=$missing"
if {$missing != 0} {error "DMA M10 interface global routes are incomplete"}
write_db "$out/dma-grt.odb"
