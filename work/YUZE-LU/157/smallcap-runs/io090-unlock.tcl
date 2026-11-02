set_thread_count 1
read_db /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-157-r-architecture/attempt089/physical/flow/results/nangate45/rarch157_B256/base/6_final.odb
unset_dont_touch [get_cells r157_io_*]
add_global_connection -net VDD -inst_pattern {r157_io_.*} -pin_pattern {VDD} -power
add_global_connection -net VSS -inst_pattern {r157_io_.*} -pin_pattern {VSS} -ground
global_connect
set n 0
foreach inst [[ord::get_db_block] getInsts] {
 if {![string match {r157_io_*} [$inst getName]]} {continue}
 foreach pg {VDD VSS} {
  set pin [$inst findITerm $pg]
  if {$pin eq "NULL" || [$pin getNet] eq "NULL" || [[$pin getNet] getName] ne $pg} {error "still unconnected: [$inst getName]/$pg"}
 }
 incr n
}
set_dont_touch [get_cells r157_io_*]
puts "CONNECTED_ADDED_BUFFERS=$n"
