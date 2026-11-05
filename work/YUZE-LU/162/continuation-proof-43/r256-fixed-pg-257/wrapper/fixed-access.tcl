set_thread_count 16
read_db {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/r256-native-reuse-251/6_final.odb}
set b [ord::get_db_block]
set tech [[ord::get_db] getTech]
write_def {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/r256-fixed-pg-257/wrapper/original.def}
write_verilog {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/r256-fixed-pg-257/wrapper/original.v}
set f [open {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/r256-fixed-pg-257/wrapper/fixed-access.tsv} w]
source {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/source-256/project/experiments/block_v1/odb_geometry.tcl}
set added_wires {}

set die [$b getDieArea]
if {[$b getDbUnitsPerMicron]!=2000 || [$die xMin]!=0 || [$die yMin]!=0} {error "Unexpected native coordinates"}
foreach {supply px} {VDD 16000 VSS 32000} {
 set n [$b findNet $supply]
 if {$n eq "NULL"} {error "Missing native supply"}
 set rails {}
 foreach sw [$n getSWires] {foreach box [$sw getWires] {
  if {![$box isVia] && [[$box getTechLayer] getName] eq "metal7" && [$box xMax]-[$box xMin]>20000 && [$box yMax]-[$box yMin]==2800} {
   lappend rails [list [$box xMin] [$box yMin] [$box xMax] [$box yMax]]
  }
 }}
 if {![llength $rails]} {error "No supported original M7 supply rails"}
 set wire [odb::dbSWire_create $n ROUTED]
 lappend added_wires [list $supply $wire]
 set metal10 [$tech findLayer metal10]
 set bottom 16000;set top [expr {[$die yMax]-16000}]
 odb::dbSBox_create $wire $metal10 [expr {$px-2000}] $bottom [expr {$px+2000}] $top STRIPE
 puts $f "STRAP\t$supply\tmetal10\t[expr {$px-2000}]\t$bottom\t[expr {$px+2000}]\t$top"
 foreach rail $rails {
  lassign $rail x0 y0 x1 y1
  set x [expr {$x0+800}];set y [expr {($y0+$y1)/2}]
  if {$px+2400 >= $x || $y-800<$bottom || $y+800>$top} {error "Fixed bridge outside reserved periphery"}
  odb::dbSBox_create $wire [$tech findLayer metal8] [expr {$px-400}] [expr {$y-400}] [expr {$x+400}] [expr {$y+400}] STRIPE
  foreach {v vx} [list via7_0 $x via8_0 $px via9_0 $px] {
   set via [$tech findVia $v];if {$via eq "NULL"} {error "Missing native via $v"}
   odb::dbSBox_create $wire $via $vx $y STRIPE
   puts $f "VIA\t$supply\t$v\t$vx\t$y"
  }
  puts $f "BRIDGE\t$supply\tmetal8\t[expr {$px-400}]\t[expr {$y-400}]\t[expr {$x+400}]\t[expr {$y+400}]"
 }
 # A fixed M10 access box on the 4um upper-routing grid, inside the strap.
 set port [$b findBTerm $supply]
 if {$port eq "NULL" || [$port getNet] ne $n || [$port getSigType] ne [$n getSigType]} {error "Missing original typed supply port"}
 set pin [odb::dbBPin_create $port];$pin setPlacementStatus FIRM
 odb::dbBox_create $pin $metal10 [expr {$px-2000}] 22000 [expr {$px+2000}] 26000
}
close $f
set s [open {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/r256-fixed-pg-257/wrapper/actual-added-geometry.tsv} w]
foreach pair $added_wires {lassign $pair net wire;foreach box [$wire getWires] {bvgeom::db_box $s $net $box fixed-pg}}
close $s
write_def {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/r256-fixed-pg-257/wrapper/wrapper.def}
write_db {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/r256-fixed-pg-257/wrapper/wrapper.odb}
write_verilog {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/r256-fixed-pg-257/wrapper/wrapper.v}
drt::check_drc_cmd {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/r256-fixed-pg-257/wrapper/native-fragmented-drc.rpt} 0 0 0 0 fixed_pg_access
