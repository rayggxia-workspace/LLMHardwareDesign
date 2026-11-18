source /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/c-exact-signal-footprint.tcl
foreach bt [[ord::get_db_block] getBTerms] {
 if {[$bt getSigType] in {POWER GROUND}} {continue}
 foreach bp [$bt getBPins] {$bp setPlacementStatus FIRM}
}
orfs_write_db $::env(RESULTS_DIR)/3_2_place_iop.odb
puts EXACT_FIXED_SIGNAL_PINS_REWRITTEN_TO_IO_CHECKPOINT
