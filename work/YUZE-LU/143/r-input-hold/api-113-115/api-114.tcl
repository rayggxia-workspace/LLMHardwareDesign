set_thread_count 1
puts "PUBLIC_CELL_COMMANDS=[lsort [info commands *cell*]]"
puts "RSZ_CELL_COMMANDS=[lsort [info commands rsz::*cell*]]"
puts "STA_REPLACE_COMMANDS=[lsort [info commands sta::*replace*]]"
puts "ODB_SWAP_COMMANDS=[lsort [info commands odb::*swapMaster*]]"
foreach command {replace_cell rsz::replace_cell sta::replace_cell} {
 if {[llength [info commands $command]]} {
  puts "HELP=$command";help $command
  if {[catch {info body $command} body]} {puts "BODY_NOT_TCL=$body"} else {puts $body}
 }
}
