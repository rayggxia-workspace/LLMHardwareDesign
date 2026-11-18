read_db /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/runs/C-v18-donly-m0.04-d0.025/flow/results/nangate45/c-overlay-current/base/4_cts.odb
set b [ord::get_db_block]
foreach name {_336444_ place45713 place45712 place45711 place45710 place14159} {
 set i [$b findInst $name]
 puts "CELL $name [[$i getMaster] getName] [$i getLocation]"
 foreach it [$i getITerms] {
  if {[[$it getMTerm] getIoType] ne "OUTPUT"} {continue}
  set net [$it getNet]
  puts "NET [$net getName]"
  foreach dst [$net getITerms] {
   set di [$dst getInst]
   puts "TERM [$di getName] [[$dst getMTerm] getName] [[$di getMaster] getName] [$di getLocation]"
  }
  foreach bt [$net getBTerms] {puts "BTERM [$bt getName]"}
 }
}