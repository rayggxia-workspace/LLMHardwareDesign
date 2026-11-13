set_thread_count $::env(SLURM_CPUS_PER_TASK)
read_db $::env(NATIVE_DMA_GRT)
set_routing_layers -signal metal2-metal10 -clock metal4-metal10
read_guides $::env(NATIVE_DMA_GUIDES)
set out $::env(NATIVE_DMA_OUTPUT)
detailed_route -output_drc "$out/drc.rpt" -output_guide_coverage "$out/coverage.csv" -droute_end_iter 24 -verbose 1
set block [ord::get_db_block]
set rows [open $::env(NATIVE_DMA_LANDINGS) r]
set endpoint_file [open "$out/routes.tsv" w]
puts $endpoint_file "pin\tnet\trole\tconnected_route_object\tx0\ty0\tx1\ty1"
set missing 0
while {[gets $rows line] >= 0} {
    lassign [split $line "\t"] name direction x0 y0 x1 y1
    set term [$block findBTerm $name]
    set net [$term getNet]
    set pad [lindex [$term getBPins] 0]
    set shape [lindex [$pad getBoxes] 0]
    if {[llength [$term getBPins]] != 1 || [llength [$pad getBoxes]] != 1
        || [[$shape getTechLayer] getRoutingLevel] != 10
        || [list [$shape xMin] [$shape yMin] [$shape xMax] [$shape yMax]] ne [list $x0 $y0 $x1 $y1]} {
        error "M10 landing changed on $name"
    }
    set wire [$net getWire]
    set present [expr {$wire ne "NULL"}]
    if {!$present} {incr missing}
    puts $endpoint_file [join [list $name [$net getName] $direction $present $x0 $y0 $x1 $y1] "\t"]
}
close $rows
close $endpoint_file
puts "DMA_M10_DETAIL_ROUTE missing_wire_objects=$missing"
write_db "$out/dma-detail.odb"
if {$missing != 0} {error "missing routed wire objects on the DMA interface"}
