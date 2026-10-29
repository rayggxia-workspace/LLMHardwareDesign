# Three genuine internal-C pin corrections on existing own-net via landings.
# Re-encode only these actual nets, keeping every original via and all wire
# rectangles except eight explicitly identified terminal stubs. No invented via.
set b [ord::get_db_block];set tech [ord::get_db_tech]
if {[$b getDbUnitsPerMicron]!=2000} {error "Unexpected source DBU"}
set specs {
 {bit_1382013 metal5 {3628660 1367380 3628940 1367660} {3647330 1367520 3647610 1367800} wire32356 Z 33}
 {bit_6907 metal6 {2956660 1367380 2956940 1367660} {2954610 1366400 2954890 1366680} wire246835 A 293}
 {bit_1389626 metal6 {3713780 1161300 3714060 1161580} {3713970 1161600 3714250 1161880} wire230167 Z 34}
}
set removed [dict create \
 bit_1382013 {{metal5 3628710 1367380 3629690 1367660} {metal5 3629410 1367380 3629690 1367800} {metal5 3629410 1367520 3647610 1367800}} \
 bit_6907 {{metal6 2956570 1367520 2956850 1368280} {metal6 2954610 1368000 2956850 1368280} {metal6 2954610 1366400 2954890 1368280}} \
 bit_1389626 {{metal6 3713830 1161300 3714250 1161580} {metal6 3713970 1161300 3714250 1161880}}]
set all_records {};set vf [open $out/original_actual_vias.tsv w]
puts $vf "net\tvia\tkind\tx_dbu\ty_dbu\tlayer\tx0_relative\ty0_relative\tx1_relative\ty1_relative"
foreach spec $specs {
 lassign $spec pin layer oldbox newbox instance port nwire
 set n [$b findNet $pin];set bt [$b findBTerm $pin]
 if {$n eq "NULL" || $bt eq "NULL" || [$bt getNet] ne $n || [llength [$n getBTerms]]!=1 || [llength [$n getITerms]]!=1 || [$n getSigType] ne "SIGNAL" || [$n getNonDefaultRule] ne "NULL"} {error "Actual original net/peer contract mismatch: $pin"}
 set it [lindex [$n getITerms] 0]
 if {[[$it getInst] getName] ne $instance || [[$it getMTerm] getName] ne $port} {error "Unexpected real internal endpoint: $pin"}
 set boxes {};foreach bp [$bt getBPins] {foreach box [$bp getBoxes] {lappend boxes $box}}
 if {[llength $boxes]!=1} {error "Expected one original signal pin rectangle"}
 set box [lindex $boxes 0]
 if {[[$box getTechLayer] getName] ne $layer || [list [$box xMin] [$box yMin] [$box xMax] [$box yMax]] ne $oldbox} {error "Original pin rectangle differs: $pin"}
 set wire [$n getWire];if {$wire eq "NULL"} {error "No original route"}
 set itr [odb::dbWirePathItr];set path [odb::dbWirePath];set ps [odb::dbWirePathShape]
 set records {};set nw 0;set nr 0;set landing 0
 $itr begin $wire
 while {[$itr getNextPath $path]} {while {[$itr getNextShape $ps]} {
  set s [odb::dbWirePathShape_shape_get $ps]
  if {[$s isVia]} {
   set kind TECH;set v [$s getTechVia];if {$v eq "NULL"} {set kind BLOCK;set v [$s getVia]};lassign [$s getViaXY] x y
   set bottom {};set level 1000
   foreach box [$v getBoxes] {
    set ly [$box getTechLayer];set name [$ly getName];set lev [$ly getRoutingLevel]
    if {$lev>0 && $lev<$level} {set level $lev;set bottom $ly}
    puts $vf [join [list $pin [$v getName] $kind $x $y $name [$box xMin] [$box yMin] [$box xMax] [$box yMax]] "\t"]
    if {$name eq $layer && [list [expr {[$box xMin]+$x}] [expr {[$box yMin]+$y}] [expr {[$box xMax]+$x}] [expr {[$box yMax]+$y}]] eq $newbox} {incr landing}
   }
   if {$bottom eq ""} {error "No actual bottom routing layer"}
   lappend records [list VIA $bottom $kind $v $x $y]
  } else {
   incr nw;set ly [$s getTechLayer];set name [$ly getName]
   set rect [list $name [$s xMin] [$s yMin] [$s xMax] [$s yMax]]
   if {$rect in [dict get $removed $pin]} {incr nr;continue}
   set width [$ly getWidth];set dx [expr {[$s xMax]-[$s xMin]}];set dy [expr {[$s yMax]-[$s yMin]}]
   if {min($dx,$dy)!=$width || $dx==$dy || $width%2} {error "Non-default/square original wire needs a distinct exact implementation"}
   if {$dx>$dy} {set a [expr {[$s xMin]+$width/2}];set c [expr {[$s xMax]-$width/2}];set y [expr {([$s yMin]+[$s yMax])/2}];set xy [list $a $y $c $y]} else {set x [expr {([$s xMin]+[$s xMax])/2}];set a [expr {[$s yMin]+$width/2}];set c [expr {[$s yMax]-$width/2}];set xy [list $x $a $x $c]}
   lappend records [list WIRE $ly {*}$xy]
  }
 }}
 if {$landing!=1 || $nw!=$nwire || $nr!=[llength [dict get $removed $pin]]} {error "Exact actual via/stub preflight failed: $pin"}
 dict set all_records $pin $records
}
close $vf
# No edit occurs until all three actual original nets pass preflight.
foreach spec $specs {
 lassign $spec pin layer oldbox newbox instance port nwire
 set n [$b findNet $pin];odb::dbWire_destroy [$n getWire]
 set w [odb::dbWire_create $n];set enc [odb::dbWireEncoder];$enc begin $w
 foreach rec [dict get $all_records $pin] {
  set kind [lindex $rec 0];set ly [lindex $rec 1];$enc newPath $ly ROUTED
  if {$kind eq "WIRE"} {lassign [lrange $rec 2 end] x y xx yy;$enc addPoint $x $y;$enc addPoint $xx $yy} else {
   lassign [lrange $rec 2 end] vk v x y;$enc addPoint $x $y
   if {$vk eq "TECH"} {$enc addTechVia $v} else {$enc addVia $v}
  }
 };$enc end
 lassign $newbox x0 y0 x1 y1
 place_pin -pin_name $pin -layer $layer -location [list [expr {($x0+$x1)/4000.}] [expr {($y0+$y1)/4000.}]] -pin_size {.14 .14}
 set boxes {};foreach bp [[$b findBTerm $pin] getBPins] {foreach box [$bp getBoxes] {lappend boxes $box}}
 if {[llength $boxes]!=1 || [list [[lindex $boxes 0] xMin] [[lindex $boxes 0] yMin] [[lindex $boxes 0] xMax] [[lindex $boxes 0] yMax]] ne $newbox} {error "Actual new pin snapped/clamped"}
}
puts "ACTUAL_3_PIN_VIA_TIP_ECO_8_TERMINAL_WIRES_REMOVED_REQUIRES_INDEPENDENT_DRC_CONNECTIVITY_RCX_STA"
