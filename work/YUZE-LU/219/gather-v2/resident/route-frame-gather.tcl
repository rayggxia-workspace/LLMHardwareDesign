set_thread_count $::env(SLURM_CPUS_PER_TASK)
set stage $::env(GATHER_PLACE)
set out $::env(GATHER_ROUTE)
read_db "$stage/staged-u.odb"
set block [ord::get_db_block]
# Remove only geometry-less boundary objects from this partial routing copy.
# Retain all internal terminals and the staged placement for product closure.
set detached [open "$out/unplaced-boundaries.tsv" w]
foreach term [$block getBTerms] {
    if {![llength [$term getBPins]]} {
        puts $detached "[$term getName]\t[$term getIoType]"
        odb::dbBTerm_destroy $term
    }
}
close $detached
# Constants shared only inside the candidate are outside the 650-net experiment.
# Remove their internal connections from this routing copy; Gather output ties
# have dedicated signal nets and remain present.
foreach name {one_ zero_} {
    set net [$block findNet $name]
    if {$net eq "NULL"} {continue}
    if {[llength [$net getBTerms]]} {error "Global constant is a placed interface $name"}
    odb::dbNet_destroy $net
}


set rows [open "$stage/landings.tsv" r]
set directed [open "$out/dma-landings.tsv" w]
set nets {}
while {[gets $rows row]>=0} {
    lassign [split $row "\t"] name x0 y0 x1 y1
    if {![string match dma_* $name]} {continue}
    set port [$block findBTerm $name]
    set net [$port getNet]
    lappend nets [$net getName]
    puts $directed [join [list $name [$port getIoType] $x0 $y0 $x1 $y1] "\t"]
}
close $rows
close $directed
if {[llength [lsort -unique $nets]]!=650} {error "Gather terminal alias"}
set manifest [open "$out/staged-ports.tsv" w]
puts $manifest "pin\tnet\trole\tx0\ty0\tx1\ty1"
set rows [open "$out/dma-landings.tsv" r]
while {[gets $rows row]>=0} {
    lassign [split $row "\t"] name role x0 y0 x1 y1
    set port [$block findBTerm $name]
    set boxes [[lindex [$port getBPins] 0] getBoxes]
    set box [lindex $boxes 0]
    if {[llength $boxes]!=1 || [[$box getTechLayer] getRoutingLevel]!=10
        || [list [$box xMin] [$box yMin] [$box xMax] [$box yMax]] ne [list $x0 $y0 $x1 $y1]} {
        error "Invalid candidate M10 geometry for $name"
    }
    puts $manifest [join [list $name [[$port getNet] getName] $role $x0 $y0 $x1 $y1] "\t"]
}
close $rows
close $manifest

set_routing_layers -signal metal2-metal10 -clock metal4-metal10
set_nets_to_route $nets
global_route -congestion_iterations 2 -guide_file "$out/route.guide" -congestion_report_file "$out/congestion.rpt" -allow_congestion
set missing {}
foreach name $nets {
    if {![llength [[$block findNet $name] getGuides]]} {lappend missing $name}
}
if {[llength $missing]} {error "Gather nets missing guides: $missing"}
write_db "$out/u-grt.odb"
puts "GATHER_GLOBAL_ROUTES 650"

