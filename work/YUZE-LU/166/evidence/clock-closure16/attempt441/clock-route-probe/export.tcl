set_thread_count 16
read_db {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-166-r-local-state/attempt392/physical/flow/results/nangate45/r166_1024/base/6_final.odb}
help read_def
set block [ord::get_db_block]
set f [open clock-nets.tsv w]
set clocks 0
foreach net [$block getNets] {
 if {[$net getSigType] eq "CLOCK"} {
  if {[$net getWire] eq "NULL"} {error "Clock net has no source wire"}
  puts $f "[$net getName]	[$net getWireType]";incr clocks
 }
}
close $f
if {$clocks==0 || [[[$block findBTerm clk] getNet] getSigType] ne "CLOCK"} {error "Clock classification missing"}
set dffs 0
foreach inst [$block getInsts] {
 if {[string match DFF* [[$inst getMaster] getName]]} {
  set ck [$inst findITerm CK]
  if {$ck eq "NULL" || [$ck getNet] eq "NULL" || [[$ck getNet] getSigType] ne "CLOCK"} {error "Unclassified DFF clock"}
  incr dffs
 }
}
puts "R166_FIXED_CLOCK_PROBE_SOURCE; clock_nets=$clocks; dffs=$dffs"
write_def before.def
