set root /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu
read_db /public/home/yuzelu/project-circuit/yzl-cu-overlay-physical-20261116/C/flow/results/nangate45/c-overlay-current/base/4_cts.odb
source $root/geometry.tcl
geometry_snapshot $root/footprint-roundtrip-before.tsv
source $root/c-exact-signal-footprint.tcl
geometry_snapshot $root/footprint-roundtrip-after.tsv
exec cmp $root/footprint-roundtrip-before.tsv $root/footprint-roundtrip-after.tsv
puts EXACT_FOOTPRINT_ROUNDTRIP_PASS
