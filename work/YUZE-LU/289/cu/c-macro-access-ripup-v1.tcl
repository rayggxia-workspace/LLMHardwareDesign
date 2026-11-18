# Proven access-recovery scope: S req_data128 + changed dotmaster signal nets.
# Apply after edits/new dotcut OBS and before guide generation + detailed_route.
set access_block [ord::get_db_block]
set access_s [$access_block findInst services.store.leaf]
if {$access_s eq "NULL"} {error "Expected exact C S macro instance"}
set access_nets {};set access_s_count 0;set access_dot_count 0
foreach it [$access_s getITerms] {
 if {[regexp {^req_data\[([0-9]+)\]$} [[$it getMTerm] getName]]} {
  incr access_s_count
  set n [$it getNet]
  if {$n eq "NULL"} {error "Unconnected C S req_data input"}
  dict set access_nets [$n getName] [list $n S_request]
 }
}
if {$access_s_count!=128} {error "C S req_data scope changed"}
foreach i [$access_block getInsts] {
 if {[[$i getMaster] getName] ne "e_s32_pipeline_128"} {continue}
 incr access_dot_count
 foreach it [$i getITerms] {
  set n [$it getNet]
  if {$n ne "NULL" && [$n getSigType] ni {POWER GROUND}} {dict set access_nets [$n getName] [list $n changed_dot_master]}
 }
}
if {$access_dot_count!=1} {error "C dot macro instance scope changed"}
set access_f [open macro-access-ripped.tsv w]
puts $access_f "net\treason\thad_wire"
set access_ripped 0
foreach {name data} $access_nets {
 lassign $data n reason
 set w [$n getWire];set had [expr {$w ne "NULL"}]
 if {$had} {odb::dbWire_destroy $w;incr access_ripped}
 puts $access_f "$name\t$reason\t$had"
}
close $access_f
puts "C_MACRO_ACCESS_RECOVERY nets=[dict size $access_nets] ripped=$access_ripped"
