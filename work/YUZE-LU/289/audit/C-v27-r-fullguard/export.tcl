read_db /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/runs/C-v27-joint-e20-h30/flow/results/nangate45/c-overlay-current/base/6_final.odb
set db [ord::get_db]
set f [open master-geometry.tsv w]
foreach name {r_stream_local} {
set m [$db findMaster $name]
puts $f "MASTER	$name	[$m getWidth]	[$m getHeight]"
foreach box [$m getObstructions] {
set layer [[$box getTechLayer] getName]
if {$layer in {metal7 metal8 metal9 metal10 via7 via8 via9}} {puts $f [join [list OBS $name $layer [$box xMin] [$box yMin] [$box xMax] [$box yMax]] "	"]}
}
foreach mt [$m getMTerms] {foreach mp [$mt getMPins] {foreach box [$mp getGeometry] {
set layer [[$box getTechLayer] getName]
if {$layer in {metal7 metal8 metal9 metal10 via7 via8 via9}} {puts $f [join [list PIN $name $layer [$box xMin] [$box yMin] [$box xMax] [$box yMax] [$mt getName]] "	"]}
}}}
}
close $f
