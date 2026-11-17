# Replaces historical access-pins.tcl: preserve exact CTS endpoint geometry.
source /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/geometry.tcl
geometry_snapshot $::env(RESULTS_DIR)/geometry-before.tsv
set b [ord::get_db_block]
set kind [dict get [dict create cfj_group_c_memory_legacy C u_n32_controlled_dma_64 U] [$b getName]]
set f [open /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/$kind-outputs.txt]
set out [open $::env(RESULTS_DIR)/output-swaps.tsv w]
puts $out "port\tinstance\told_master\tnew_master"
set n 0
while {[gets $f p] >= 0} {
 set p [string trim $p]
 if {$p eq ""} {continue}
 set term [$b findBTerm $p]
 if {$term eq "NULL" || [$term getIoType] ne "OUTPUT"} {error "Invalid selected output $p"}
 set net [$term getNet]
 set drivers {}
 foreach it [$net getITerms] {
  if {[[$it getMTerm] getIoType] eq "OUTPUT"} {lappend drivers [$it getInst]}
 }
 if {[llength $drivers] != 1} {error "Expected exactly one output driver on $p"}
 set inst [lindex $drivers 0]
 set old [[$inst getMaster] getName]
 if {![regexp {^(BUF|INV|CLKBUF)_X([0-9]+)$} $old -> family strength]} {error "Nonbuffer output driver $p: $old; equivalent cell proof required"}
 set new $old
 if {$strength < 8} {
  set new ${family}_X8
  set master [[ord::get_db] findMaster $new]
  if {$master eq "NULL"} {error "No legal X8 equivalent: $new"}
  replace_cell [$inst getName] $new
 }
 # Preserve selected final stage under subsequent timing/power optimization.
 # Instance stays editable so upstream load repair can add legal buffers.
 set_dont_touch [get_nets [$net getName]]
 puts $out "$p\t[$inst getName]\t$old\t$new"
 incr n
}
close $f
close $out
if {$n != 153} {error "Selected endpoint count changed: $n"}
global_connect
detailed_placement
check_placement -verbose
geometry_snapshot $::env(RESULTS_DIR)/geometry-after-eco.tsv
puts "ISSUE289_OUTPUTS_UPGRADED $n"
