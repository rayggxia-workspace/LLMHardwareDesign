read_db $::env(PINXY_ODB)
set b [ord::get_db_block]
set f [open "data/$::env(PINXY_CASE)/anchors.tsv" w]
puts $f "pin\tnet_id\tinst\tmterm\tdirection\tx\ty\tlayers\tdepth"
proc walk {pin net dir depth seen} {
 global f
 if {$depth>12 || [$net getId] in $seen} {return}
 lappend seen [$net getId]
 foreach it [$net getITerms] {
  if {[$it getIoType] ne $dir} {continue}
  set inst [$it getInst];set name [[$inst getMaster] getName]
  set isbuf [regexp {^(BUF|INV|CLKBUF)_} $name]
  if {$isbuf && $depth<12} {
   foreach other [$inst getITerms] {if {[$other getSigType] ni {POWER GROUND} && [$other getIoType] ne $dir && [$other getNet] ne "NULL"} {walk $pin [$other getNet] $dir [expr {$depth+1}] $seen}}
  } else {
   lassign [$it getAvgXY] ok x y
   set layers {};foreach g [$it getGeometries] {lappend layers [[lindex $g 0] getName]}
   puts $f "$pin\t[$net getId]\t[$inst getName]\t[[$it getMTerm] getName]\t[$it getIoType]\t$x\t$y\t[join [lsort -unique $layers] ,]\t$depth"
  }
 }
}
foreach bt [$b getBTerms] {
 if {[$bt getSigType] in {POWER GROUND} || [$bt getName] eq "clk"} {continue}
 # Direction selects receiver ITerms for inputs, driver ITerms for outputs.
 walk [$bt getName] [$bt getNet] [$bt getIoType] 0 {}
}
close $f
puts "ANCHORS_COMPLETE"
