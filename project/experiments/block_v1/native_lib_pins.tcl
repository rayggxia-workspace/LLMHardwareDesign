# The installed OpenSTA returns local lib-pin names from get_full_name.
# Resolve exactly one cell in the declared library, then construct the fully
# scoped identity from that exact query and its returned local pin name.
set scoped_cells [get_lib_cells ${wanted_library}/${wanted_master}]
if {[llength $scoped_cells]!=1} {error "Missing or ambiguous exact library/cell"}
if {[llength [get_lib_pins -quiet __BV1_no_library__/${wanted_master}/*]]!=0} {
  error "Wrong-library scoped query unexpectedly returned pins"
}
if {[llength [get_lib_pins -quiet ${wanted_library}/__BV1_no_cell__/*]]!=0} {
  error "Wrong-cell scoped query unexpectedly returned pins"
}
set pins [get_lib_pins ${wanted_library}/${wanted_master}/*]
if {[llength $pins]==0} {error "Exact library/cell query returned no pins"}
set stream [open lib-interface.tsv w]
foreach pin $pins {
  set local_name [get_full_name $pin]
  if {[string first / $local_name]>=0} {error "Unexpected nonlocal lib-pin name"}
  puts $stream "${wanted_library}/${wanted_master}/${local_name}\t[get_property $pin direction]"
}
close $stream
