set_thread_count 16
read_db {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/block-v1-20261030-588/tasks/revision300-route-v/flow/results/nangate45/bv1_block_v1_v/base/5_1_grt.odb}
proc signal_pins {i} {
  set rows {}
  foreach t [$i getITerms] {
    set m [$t getMTerm]
    if {[$m getSigType] in {POWER GROUND}} {continue}
    set n [$t getNet]
    lappend rows [list [$m getName] [expr {$n eq "NULL" ? "NULL" : [$n getName]}]]
  }
  return [lsort $rows]
}
set b [ord::get_db_block]
set f [open driver-probe.tsv w]
set i [$b findInst {place84364}]
if {$i eq "NULL" || [[$i getMaster] getName] ne "BUF_X2"} {error "Measured GRT driver place84364 differs from final"}
set pins [signal_pins $i]
set old [$i getMaster]
set replacement [[ord::get_db] findMaster BUF_X4]
if {$replacement eq "NULL" || ![$i swapMaster $replacement]} {error "Measured driver swap failed place84364"}
if {[signal_pins $i] ne $pins} {error "Measured driver signal connectivity changed place84364"}
puts $f [join [list place84364 BUF_X2 BUF_X4 [$old getWidth] [$old getHeight] [$replacement getWidth] [$replacement getHeight]] "\t"]
set i [$b findInst {place76249}]
if {$i eq "NULL" || [[$i getMaster] getName] ne "BUF_X1"} {error "Measured GRT driver place76249 differs from final"}
set pins [signal_pins $i]
set old [$i getMaster]
set replacement [[ord::get_db] findMaster BUF_X2]
if {$replacement eq "NULL" || ![$i swapMaster $replacement]} {error "Measured driver swap failed place76249"}
if {[signal_pins $i] ne $pins} {error "Measured driver signal connectivity changed place76249"}
puts $f [join [list place76249 BUF_X1 BUF_X2 [$old getWidth] [$old getHeight] [$replacement getWidth] [$replacement getHeight]] "\t"]
close $f
