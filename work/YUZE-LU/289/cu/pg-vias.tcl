read_db /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/runs/U-v6-ctsdelay-x8-seed0/flow/results/nangate45/u-overlay-current/base/5_1_grt.odb
set f [open /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/pg-via-definitions.tsv w]
foreach v [[ord::get_db_tech] getVias] {
 foreach r [$v getBoxes] {puts $f [join [list TECHVIA [$v getName] [[$r getTechLayer] getName] [$r xMin] [$r yMin] [$r xMax] [$r yMax]] "\t"]}
}
foreach v [[ord::get_db_block] getVias] {
 if {![string match *6_7* [$v getName]]} {continue}
 foreach r [$v getBoxes] {puts $f [join [list BLOCKVIA [$v getName] [[$r getTechLayer] getName] [$r xMin] [$r yMin] [$r xMax] [$r yMax]] "\t"]}
}
close $f
