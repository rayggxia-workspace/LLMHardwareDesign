read_db $::env(ROUTER_PROBE_ODB)
source project/experiments/block_v1/odb_geometry.tcl
bvgeom::export $::env(ROUTER_PROBE_OUT) [list $::env(ROUTER_PROBE_NET)]
