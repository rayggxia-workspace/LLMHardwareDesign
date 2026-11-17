read_db /public/home/yuzelu/project-circuit/yzl-c-segment-250mhz-20261116/flow/results/nangate45/c-native-frame/base/6_final.odb
set f [open G-native-terms.tsv w]
puts $f "endpoint\tnet\tinstance\tmaster\tpin\tdirection"
foreach inst [[ord::get_db_block] getInsts] {
 if {[[$inst getMaster] getName] ne "block_v2_g"} {continue}
 foreach term [$inst getITerms] {
  set pin [[$term getMTerm] getName]
  if {![string match "out_*" $pin]} {continue}
  set net [$term getNet]
  if {$net eq "NULL"} {continue}
  foreach t [$net getITerms] {
   set it [$t getInst];set mt [$t getMTerm]
   puts $f "C0.G.$pin\t[$net getName]\t[$it getName]\t[[$it getMaster] getName]\t[$mt getName]\t[$mt getIoType]"
  }
 }
}
close $f
puts G_NATIVE_COMPLETE
