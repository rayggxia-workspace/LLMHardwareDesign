read_db /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/runs/U-v14-guardant-f67-h3-u1.2/flow/results/nangate45/u-overlay-current/base/6_final.odb
foreach rule [[ord::get_db_block] getNonDefaultRules] {
 puts "RULE [$rule getName] HARD [$rule getHardSpacing]"
 foreach layer [[ord::get_db_tech] getLayers] {
  if {[$layer getRoutingLevel]<1} {continue}
  set lr [$rule getLayerRule $layer]
  puts "LAYER [$layer getName] WIDTH [$lr getWidth] TECHWIDTH [$layer getWidth] SPACING [$lr getSpacing] TECHSPACE [$layer getSpacing]"
 }
}