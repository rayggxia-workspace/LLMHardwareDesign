set root /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu
read_db $::env(CU_SEED)/4_1_pre_repair_setup_hold.odb
source $root/c-inject-actual-cuts.tcl
set b [ord::get_db_block]
set sink [[$b findInst input1249] findITerm A]
set prev [$sink getNet]
$sink disconnect
lassign [[$b findInst input1249] getLocation] x y
set master [[ord::get_db] findMaster CLKBUF_X1]
for {set n 0} {$n<$::env(CU_RESET_N)} {incr n} {
 set name i289_reset_delay_$n
 set i [odb::dbInst_create $b $master $name]
 $i setLocation $x $y
 $i setPlacementStatus PLACED
 set net [odb::dbNet_create $b ${name}_net]
 [$i findITerm A] connect $prev
 [$i findITerm Z] connect $net
 set prev $net
}
$sink connect $prev
foreach name {place45713 place45712 place45711 place45710} {
 set i [$b findInst $name]
 if {$i eq "NULL" || [[$i getMaster] getName] ne "BUF_X8"} {error "Trace driver mismatch $name"}
 $i swapMaster [[ord::get_db] findMaster BUF_X$::env(CU_TRACE_X)]
}
write_db edited.odb