# Continue a previously repaired, pinned post-GRT database without repeating
# the initial RX delay chains or reverting successful cell-size repairs.
set block [ord::get_db_block]
set lease [$block findInst services.lease]
if {$lease eq "NULL"} {error "Pinned T instance not found"}
set macro_box [$lease getBBox]
set lx [$macro_box xMin]
set ly [$macro_box yMin]
set hx [$macro_box xMax]
set hy [$macro_box yMax]
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
  # Place the final stage near the nearest outside edge of the hard macro.
  # Pins are internal M10 shapes; buffers must stay in legal external rows.
  set pin_box [$pin getBBox]
  set px [expr {([$pin_box xMin]+[$pin_box xMax])/2}]
  set py [expr {([$pin_box yMin]+[$pin_box yMax])/2}]
  set bw [[$inst getMaster] getWidth]
  set bh [[$inst getMaster] getHeight]
  set choices [list [list [expr {$px-$lx}] [expr {$lx-$bw-16000}] [expr {$py-$bh/2}]] \
                    [list [expr {$hx-$px}] [expr {$hx+16000}] [expr {$py-$bh/2}]] \
                    [list [expr {$py-$ly}] [expr {$px-$bw/2}] [expr {$ly-$bh-16000}]] \
                    [list [expr {$hy-$py}] [expr {$px-$bw/2}] [expr {$hy+16000}]]]
  set best [lindex [lsort -integer -index 0 $choices] 0]
  $inst setPlacementStatus PLACED
  $inst setLocation [lindex $best 1] [lindex $best 2]
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
set report [open $::env(RESULTS_DIR)/j-terminal-drivers.tsv a]
foreach name [lsort -unique $drivers] {
  set inst [$block findInst $name]
  set box [$inst getBBox]
  $inst setPlacementStatus FIRM
  puts $report "LEGALIZED\t$name\t[$box xMin]\t[$box yMin]\tFIRM"
}
close $report
puts "J64_TERMINAL_DRIVERS $count minimum_BUF_X16"
