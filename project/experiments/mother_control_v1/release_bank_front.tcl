# Release only the actual temporary reservations recorded by the floorplanner.
set block [ord::get_db_block]
set stream [open $mc_bank_reservation_inventory r]
set boxes {}
while {[gets $stream line]>=0} {
 set box [split $line "\t"]
 if {[llength $box]!=4} {error "Invalid bank-front inventory"}
 lappend boxes $box
}
close $stream
set removed 0
foreach blockage [$block getBlockages] {
 set b [$blockage getBBox]
 set box [list [$b xMin] [$b yMin] [$b xMax] [$b yMax]]
 if {[lsearch -exact $boxes $box]>=0} {odb::dbBlockage_destroy $blockage;incr removed}
}
if {$removed!=[llength $boxes] || $removed==0} {error "Bank-front reservation release mismatch"}
puts "MC_RELEASED_BANK_FRONT_RECTANGLES $removed"
