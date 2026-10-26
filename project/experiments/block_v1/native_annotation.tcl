# Resolve every native unannotated driver while the exact STA graph is loaded.
set stream [open annotation.rpt r]
set annotation_text [read $stream]
close $stream
if {![regexp {(?s)Found ([0-9]+) unannotated drivers\.\n(.*?)Found ([0-9]+) partially unannotated drivers\.} $annotation_text -> count body partial]} {
  error "Missing complete native parasitic annotation report"
}
set names {}
foreach line [split $body \n] {
  set name [string trim $line]
  if {$name ne ""} {lappend names $name}
}
if {[llength $names]!=$count} {error "Annotation driver list/count mismatch"}
set stream [open annotation-connectivity.tsv w]
foreach name $names {
  set pins [get_pins -quiet $name]
  if {![llength $pins]} {set pins [get_ports -quiet $name]}
  if {[llength $pins]!=1} {puts $stream "$name\tMISSING_OR_AMBIGUOUS";continue}
  set reached_count 0
  foreach reached [get_fanout -from $pins -flat -pin_levels 2 -trace_arcs all] {
    if {[lsearch -exact $pins $reached]<0} {incr reached_count}
  }
  puts $stream "$name\t$reached_count"
}
close $stream
