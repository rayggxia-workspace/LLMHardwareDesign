set_thread_count 16
read_db {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-166-r-local-state/attempt392/physical/flow/results/nangate45/r166_1024/base/6_final.odb}
foreach net [[ord::get_db_block] getNets] {
 if {[$net getSigType] eq "CLOCK"} {
  set wire [$net getWire]
  if {$wire eq "NULL"} {error "Source clock wire disappeared"}
  odb::dbWire_destroy $wire
 }
}
read_def -incremental {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-166-r-local-state/attempt442/clock-route-probe/fixed-clocks.def}
write_def after.def
