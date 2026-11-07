# Continue a previously repaired, pinned post-GRT database without repeating
# the initial RX delay chains or reverting successful cell-size repairs.
set block [ord::get_db_block]
set lease [$block findInst services.lease]
if {$lease eq "NULL"} {error "Pinned T instance not found"}
set drivers {}
set nets {}
set count 0
set report [open $::env(RESULTS_DIR)/j-terminal-drivers.tsv w]
foreach pin [$lease getITerms] {
  set port [[$pin getMTerm] getName]
  if {![regexp {^write_(data|index)\[[0-9]+\]$} $port]} {continue}
  set net [$pin getNet]
  set output {}
  foreach term [$net getITerms] {
    if {[$term getIoType] eq "OUTPUT"} {lappend output $term}
  }
  if {[llength $output] != 1} {error "Expected one T terminal driver: $port"}
  set inst [[lindex $output 0] getInst]
  set name [$inst getName]
  set master [[$inst getMaster] getName]
  if {$master ni {BUF_X16 BUF_X32}} {
    if {![regexp {^(BUF_X[1248]|CLKBUF_X[123])$} $master]} {error "Unexpected terminal master $master"}
    if {[replace_cell [get_cells $name] BUF_X16] != 1} {error "Terminal resize rejected"}
  }
  puts $report "$port\t$name\t$master\t[[$inst getMaster] getName]\t[$net getName]"
  lappend drivers $name
  lappend nets [$net getName]
  incr count
}
close $report
if {$count != 138} {error "Unexpected T data/index width: $count"}
global_connect
# Preserve the terminal drive strength and topology while allowing upstream
# electrical/hold repair and physical routing. This is prefabrication logic.
# Leave driver inputs repairable; protecting these cells blocks upstream
# buffering in OpenROAD. Output nets remain protected during repair.
foreach name [lsort -unique $nets] {set_dont_touch [get_nets $name]}
detailed_placement_helper
check_placement -verbose
puts "J64_TERMINAL_DRIVERS $count minimum_BUF_X16"
