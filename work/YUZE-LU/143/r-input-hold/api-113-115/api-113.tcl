set_thread_count 1
puts "SIZE_CELL_COMMAND=[info commands size_cell]"
if {[llength [info commands size_cell]]!=1} {error "Pinned OpenROAD has no size_cell command"}
help size_cell
if {[catch {info body size_cell} body]} {puts "BODY_NOT_TCL=$body"} else {puts "SIZE_CELL_BODY_BEGIN";puts $body;puts "SIZE_CELL_BODY_END"}
