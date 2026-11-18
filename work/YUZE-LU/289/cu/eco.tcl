# Requires final verified target TSV with instance,old_master,new_master.
# This is a candidate stage; no signoff is implied by successful swapping.
foreach lib $::env(INPUT_LIBS) {read_liberty $lib}
read_db $::env(INPUT_ODB)
read_sdc $::env(INPUT_SDC)
set block [ord::get_db_block]
set f [open $::env(TARGET_TSV)]
set out [open swaps.tsv w]
puts $out "instance\told_master\tnew_master"
gets $f header
while {[gets $f line] >= 0} {
 if {$line eq ""} {continue}
 lassign [split $line "\t"] name old new
 set inst [$block findInst $name]
 if {$inst eq "NULL" || [[$inst getMaster] getName] ne $old} {error "Input instance identity mismatch: $name"}
 set target [[ord::get_db] findMaster $new]
 if {$target eq "NULL"} {error "Target cell missing: $new"}
 if {![regexp {^(BUF|INV|CLKBUF)_X[0-9]+$} $old]} {error "Nonbuffer swap requires separately proven equivalent: $old"}
 if {[lindex [split $old _] 0] ne [lindex [split $new _] 0]} {error "Logic family changed"}
 if {![$inst swapMaster $target]} {error "swapMaster failed: $name"}
 puts $out "$name\t$old\t$new"
}
close $f
close $out
global_connect
detailed_placement
check_placement -verbose
write_db candidate-placed.odb
write_def candidate-placed.def
write_verilog candidate-placed.v
puts CANDIDATE_PLACED_NOT_SIGNED_OFF
