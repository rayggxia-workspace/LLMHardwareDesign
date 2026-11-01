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
set by_name [dict create]
foreach pin $pins {
  set local_name [get_full_name $pin]
  if {[dict exists $by_name $local_name]} {error "Duplicate scoped library pin"}
  dict set by_name $local_name $pin
}
set buses [open lib-buses.tsv w]
set stream [open lib-interface.tsv w]
foreach pin $pins {
  set local_name [get_full_name $pin]
  if {[string first / $local_name]>=0} {error "Unexpected nonlocal lib-pin name"}
  if {[$pin is_bus]} {
    # A typed Liberty bus container is not an additional physical pin.
    # Retain its identity and prove every member also occurs in this exact
    # scoped query with the same direction before writing the scalar view.
    set members {}
    set iterator [$pin member_iterator]
    while {[$iterator has_next]} {
      set member [$iterator next]
      set name [get_full_name $member]
      if {[$member is_bus] || ![dict exists $by_name $name]} {error "Missing/nested library bus member"}
      if {[get_property $member direction] ne [get_property $pin direction]} {error "Bus member direction mismatch"}
      if {[lsearch -exact $members $name]>=0} {error "Duplicate library bus member"}
      lappend members $name
    }
    $iterator finish
    if {[llength $members]==0} {error "Empty library bus"}
    puts $buses "${wanted_library}/${wanted_master}/${local_name}\t[get_property $pin direction]\t[join $members { }]"
    continue
  }
  puts $stream "${wanted_library}/${wanted_master}/${local_name}\t[get_property $pin direction]"
}
close $stream
close $buses
