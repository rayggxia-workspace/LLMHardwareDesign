# Read-only topology diagnostic on hash-bound optimized116 pre-ECO checkpoint.
set_thread_count 1
read_liberty /OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib
read_db {/public/home/yuzelu/project-circuit/llm_routing_analysis/worktrees/issue143-seven-block-v2-20261030/outputs/116/pnr/r/flow/results/nangate45/bv1_block_v1_r/base/issue143-targeted-pre.odb}
set block [ord::get_db_block]
set driver {$abc$4429625$auto$blifparse.cc:397:parse_blif$4540226}
foreach name [list $driver wire592286 wire592285] {
 set inst [$block findInst $name];if {$inst eq "NULL"} {error "Missing exact measured instance"}
 puts "INSTANCE $name [[$inst getMaster] getName] [$inst getLocation]"
 foreach pin [$inst getITerms] {
  set kind [[$pin getMTerm] getSigType];if {$kind in {POWER GROUND}} {continue}
  set net [$pin getNet];set terms {}
  foreach term [$net getITerms] {lappend terms "[[$term getInst] getName]/[[$term getMTerm] getName]:[[[$term getInst] getMaster] getName]"}
  puts "PIN [[$pin getMTerm] getName] NET [$net getName] TERMS [lsort $terms]"
 }
}
puts "READ_ONLY_TOPOLOGY_PASS"
