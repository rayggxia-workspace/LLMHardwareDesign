read_db {/public/home/yuzelu/PingyangHuang/issue177-s-production-20261104T023042Z/sealed/n4/flow/results/nangate45/bv1_local_s_n4/base/6_final.odb}
set block [ord::get_db_block]
set f [open input-receivers-actual.tsv w]
foreach port [$block getBTerms] {
 if {[$port getSigType] in {POWER GROUND} || [$port getIoType] ne "INPUT" || [$port getName] eq "clk"} {continue}
 set net [$port getNet];set receiver {};set diodes 0
 foreach term [$net getITerms] {
  set inst [$term getInst];set master [[$inst getMaster] getName]
  if {$master eq "ANTENNA_X1" && [[$term getMTerm] getName] eq "A"} {incr diodes;continue}
  if {$master ne "BUF_X8" || [[$term getMTerm] getName] ne "A" || $receiver ne ""} {error "Unexpected input-root load"}
  set receiver $inst
 }
 if {$receiver eq "" || $diodes!=1} {error "Incomplete actual input receiver/protection"}
 set internal [[$receiver findITerm Z] getNet]
 if {$internal eq "NULL" || [llength [$internal getITerms]]<2} {error "Disconnected receiver output"}
 puts $f "[$port getName]\t[$receiver getName]\t[$net getName]\t[$internal getName]\t[$receiver getLocation]"
}
close $f
