read_db $::env(PG_ODB)
set b [ord::get_db_block]
set f [open "$::env(PG_LABEL)-sboxes.tsv" w]
foreach rail {VDD VSS} {
 foreach sw [[$b findNet $rail] getSWires] {
  foreach box [$sw getWires] {
   if {[$box isVia]} {
    set via [$box getTechVia]
    if {$via eq "NULL"} {set via [$box getBlockVia]}
    lassign [$box getViaXY] x y
    foreach shape [$via getBoxes] {
     set layer [[$shape getTechLayer] getName]
     
     puts $f "$rail\tPGVIA:[$via getName]:$x:$y\t$layer\t[expr {[$shape xMin]+$x}]\t[expr {[$shape yMin]+$y}]\t[expr {[$shape xMax]+$x}]\t[expr {[$shape yMax]+$y}]"
    }
   } else {
    set layer [[$box getTechLayer] getName]
    
    puts $f "$rail\tPGWIRE\t$layer\t[$box xMin]\t[$box yMin]\t[$box xMax]\t[$box yMax]"
   }
  }
 }
}
close $f
puts U_PG_GEOMETRY_COMPLETE

set f [open "$::env(PG_LABEL)-bpins.tsv" w]
foreach bt [$b getBTerms] {
 if {[$bt getSigType] ni {POWER GROUND}} {continue}
 foreach p [$bt getBPins] {foreach x [$p getBoxes] {puts $f [join [list [$bt getName] [[$bt getNet] getName] [[$x getTechLayer] getName] [$x xMin] [$x yMin] [$x xMax] [$x yMax]] "\t"]}}
}
close $f
if {$::env(PG_LABEL) eq "candidate"} {
 set f [open pg-check.tsv w]
 foreach rail {VDD VSS} {set rc [catch {check_power_grid -net $rail} v];puts $f "$rail\t$rc\t$v";if {$rc || $v ne "1"} {error "PG failed $rail"}}
 close $f
}
