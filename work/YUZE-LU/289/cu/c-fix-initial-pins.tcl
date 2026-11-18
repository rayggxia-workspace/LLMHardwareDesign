read_db $::env(CU_FIXED_INPUT)
source /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/c-exact-signal-footprint.tcl
foreach bt [[ord::get_db_block] getBTerms] {
 if {[$bt getSigType] in {POWER GROUND}} {continue}
 foreach bp [$bt getBPins] {$bp setPlacementStatus FIRM}
}
write_db $::env(CU_FIXED_OUTPUT)
