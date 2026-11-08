set run $::env(ROUTER_HANDOFF)
read_lef $run/technology/research12.tech.lef
read_lef $run/upper-vias.lef
set tech [[ord::get_db] getTech]
foreach level {11 12} {
    set layer [$tech findLayer metal$level]
    if {[$layer getWidth] != $::env(ROUTER_WIRE_WIDTH)} {error "backend/router width mismatch"}
}
read_def $run/upper.def
write_db $run/upper.odb
write_def $run/upper-readback.def
source project/experiments/block_v1/odb_geometry.tcl
bvgeom::export $run/odb-geometry.tsv
