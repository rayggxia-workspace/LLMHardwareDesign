proc freeze_selected_c_outputs {} {
 set b [ord::get_db_block]
 set f [open /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/C-outputs.txt]
 set n 0
 while {[gets $f port]>=0} {
  if {[string trim $port] eq ""} {continue}
  set bt [$b findBTerm $port]
  if {$bt eq "NULL"} {error "Missing selected output $port"}
  set net [$bt getNet];set drivers {}
  foreach it [$net getITerms] {if {[[$it getMTerm] getIoType] eq "OUTPUT"} {lappend drivers [$it getInst]}}
  if {[llength $drivers]!=1} {error "Ambiguous selected driver $port"}
  set i [lindex $drivers 0]
  if {[[$i getMaster] getName] ne "BUF_X8"} {error "Selected driver not X8: $port"}
  set_dont_touch [get_cells [list [$i getName]]]
  set_dont_touch [get_nets [list [$net getName]]]
  incr n
 }
 close $f
 if {$n!=153} {error "Selected port count changed"}
 puts "SELECTED_C_OUTPUTS_EXACT_X8 $n"
}
