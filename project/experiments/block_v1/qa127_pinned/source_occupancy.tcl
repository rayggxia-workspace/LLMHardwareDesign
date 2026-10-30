# Read-only occupancy producer. The pinned project geometry helper exports
# wires, special wires and transformed instance/block pins; append all master
# OBS through each instance transform and exact net-to-port membership.
if {[catch {
  read_db $::env(BV1QA_ODB)
  source $::env(BV1QA_GEOMETRY_HELPER)
  bvgeom::export source-occupancy.tsv
  set block [ord::get_db_block]
  set stream [open source-occupancy.tsv a]
  foreach term [$block getBTerms] {
    set net [$term getNet]
    if {![bvgeom::present $net]} {error "Unconnected source boundary port"}
    puts $stream "# PORT n[$net getId] [binary encode hex [encoding convertto utf-8 [$term getName]]]"
  }
  set instances 0
  set master_boxes 0
  foreach instance [$block getInsts] {
    incr instances
    set owner i[$instance getId]
    puts $stream "# NET $owner [binary encode hex [encoding convertto utf-8 @instance/[$instance getName]]]"
    set transform [$instance getTransform]
    foreach box [[$instance getMaster] getObstructions] {
      incr master_boxes
      bvgeom::db_box $stream $owner $box instance-obstruction $transform
    }
  }
  close $stream
  set stream [open occupancy-summary.tsv w]
  puts $stream "dbu_per_um\t[$block getDbUnitsPerMicron]"
  puts $stream "native_instances\t$instances"
  puts $stream "native_master_obstruction_boxes\t$master_boxes"
  close $stream
} problem options]} {
  puts stderr $problem
  puts stderr [dict get $options -errorinfo]
  exit 1
}
exit 0
