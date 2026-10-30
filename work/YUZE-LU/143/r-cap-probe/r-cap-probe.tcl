set_thread_count 16
read_db {/public/home/yuzelu/project-circuit/llm_routing_analysis/worktrees/issue143-seven-block-v2-20261030/outputs/015/pnr/r/flow/results/nangate45/bv1_block_v1_r/base/5_1_grt.odb}
set b [ord::get_db_block]
set units [$b getDbUnitsPerMicron]
set f [open cap-drivers.tsv w]
puts $f "instance	master	net	loads	drivers	span_x_um	span_y_um	origin	origin_master	upstream_buffer_levels"
foreach name {wire681353 wire681142 wire602360 place418214 wire678974 max_cap687967 wire679781 max_cap679830 wire679309 wire681012 wire680143 wire678631} {
 set inst [$b findInst $name]
 if {$inst eq "NULL"} {error "missing cap driver $name"}
 set term [$inst findITerm Z];set net [$term getNet]
 set loads 0;set drivers 0;set xs {};set ys {}
 foreach t [$net getITerms] {
  if {[[$t getMTerm] getIoType] eq "OUTPUT"} {incr drivers} else {incr loads}
  lassign [[$t getInst] getLocation] x y;lappend xs $x;lappend ys $y
 }
 set xs [lsort -integer $xs];set ys [lsort -integer $ys]
 set dx [expr {([lindex $xs end]-[lindex $xs 0])/double($units)}]
 set dy [expr {([lindex $ys end]-[lindex $ys 0])/double($units)}]
 set origin $inst;set depth 0
 while {$depth<32 && [string match *BUF* [[$origin getMaster] getName]]} {
  set a [$origin findITerm A];if {$a eq "NULL"} {break}
  set n [$a getNet];set found {}
  foreach t [$n getITerms] {if {[[$t getMTerm] getIoType] eq "OUTPUT"} {lappend found [$t getInst]}}
  if {[llength $found]!=1} {break}
  set origin [lindex $found 0];incr depth
 }
 puts $f "$name	[[$inst getMaster] getName]	[$net getName]	$loads	$drivers	$dx	$dy	[$origin getName]	[[$origin getMaster] getName]	$depth"
}
close $f
