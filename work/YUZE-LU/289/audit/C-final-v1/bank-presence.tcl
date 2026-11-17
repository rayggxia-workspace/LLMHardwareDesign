set odb /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/runs/C-v20-native-clock4/global-candidate.odb
read_db $odb
set name s_sram_256x128_freepdk45
set m [[ord::get_db] findMaster $name]
if {$m eq "NULL"} {puts "BANK_MASTER_PRESENT 0"} else {puts "BANK_MASTER_PRESENT 1";puts "BANK_IS_BLOCK [$m isBlock]";puts "BANK_SIZE [$m getWidth] [$m getHeight]"}
set n 0
foreach i [[ord::get_db_block] getInsts] {if {[[$i getMaster] getName] eq $name} {incr n;puts "BANK_INSTANCE [$i getName] [$i getLocation] [$i getOrient]"}}
puts "BANK_TOP_INSTANCE_COUNT $n"
