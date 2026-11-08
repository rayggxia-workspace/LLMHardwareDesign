read_db $::env(ROUTER_SNAPSHOT_ODB)
set block [ord::get_db_block]
set f [open $::env(ROUTER_SNAPSHOT_INSTANCES) w]
foreach inst [$block getInsts] {
    lassign [$inst getLocation] x y
    puts $f [join [list [$inst getName] [[$inst getMaster] getName] $x $y [$inst getOrient]] "\t"]
}
close $f
set f [open $::env(ROUTER_SNAPSHOT_OWNERS) w]
foreach net [$block getNets] {
    if {![string match UPPER_* [$net getName]]} {continue}
    if {[llength [$net getBTerms]] != 0} {error "internal upper net retained an external port"}
    foreach term [$net getITerms] {
        set inst [$term getInst]
        set pin [$term getMTerm]
        puts $f [join [list [$net getName] [$pin getIoType] [$inst getName] [[$inst getMaster] getName] [$pin getName]] "\t"]
    }
}
close $f
source project/experiments/block_v1/odb_geometry.tcl
bvgeom::export $::env(ROUTER_SNAPSHOT_GEOMETRY)
