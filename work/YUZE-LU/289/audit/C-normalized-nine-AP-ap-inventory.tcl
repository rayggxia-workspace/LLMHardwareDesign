set_thread_count 8
read_db $::env(AP_SOURCE)
set b [ord::get_db_block]
set inst [$b findInst {services.store.leaf}]
set it [$inst findITerm {req_data[74]}]
puts "SOURCE $::env(AP_SOURCE)"
puts "INDEX [$inst getPinAccessIdx] PREF [$it getPrefAccessPoints]"
puts "NET [[$it getNet] getName] ORIGIN [$inst getOrigin] ORIENT [$inst getOrient]"
set total 0;set found 0
set target_mps [[$it getMTerm] getMPins]
foreach ap [$b getAccessPoints] {
 incr total
 if {[$ap getMPin] ni $target_mps} {continue}
 incr found
 set mask {}
 foreach d {NORTH SOUTH EAST WEST UP DOWN} {lappend mask $d [$ap hasAccess $d]}
 puts "AP [$ap getId] MPIN [[$ap getMPin] getId] POINT [$ap getPoint] LAYER [[$ap getLayer] getName] ACCESS $mask"
}
puts "TOTAL_AP $total S74_MP_AP $found"
