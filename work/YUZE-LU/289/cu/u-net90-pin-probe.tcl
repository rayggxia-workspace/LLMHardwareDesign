read_db /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/runs/U-v15-guardant-f67-h3-u1.2/flow/results/nangate45/u-overlay-current/base/6_final.odb
set b [ord::get_db_block]
foreach net [$b getNets] {
 if {[string map [list "\\" ""] [$net getName]] ne {datapath.legacy_rsp_data[90]}} {continue}
 puts "NET [$net getName] SIGTYPE [$net getSigType] SWIRES [llength [$net getSWires]]"
 foreach it [$net getITerms] {
  set i [$it getInst];set mt [$it getMTerm]
  puts "TERM [$i getName]/[$mt getName] [[$i getMaster] getName] SIGTYPE [$mt getSigType] IO [$mt getIoType]"
  foreach geometry [$it getGeometries] {
   lassign $geometry layer box
   puts "GEOM [$layer getName] [$box xMin] [$box yMin] [$box xMax] [$box yMax]"
  }
 }
}