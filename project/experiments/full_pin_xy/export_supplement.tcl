# Native master OBS readout with explicit, bbox-checked orthogonal transforms.
read_db $::env(PINXY_ODB)
set b [ord::get_db_block]
file mkdir supplement/$::env(PINXY_CASE)
set f [open supplement/$::env(PINXY_CASE)/instances.tsv w]
puts $f "inst\tmaster\ttype"
set o [open supplement/$::env(PINXY_CASE)/obstructions.tsv w]
puts $o "layer\tx0\ty0\tx1\ty1\tnet_id\tkind\tinst"
proc rotate {x y orient} {
 switch $orient {
  R0 {return [list $x $y]}
  R90 {return [list [expr {-$y}] $x]}
  R180 {return [list [expr {-$x}] [expr {-$y}]]}
  R270 {return [list $y [expr {-$x}]]}
  MX {return [list $x [expr {-$y}]]}
  MY {return [list [expr {-$x}] $y]}
  MXR90 {return [list $y $x]}
  MYR90 {return [list [expr {-$y}] [expr {-$x}]]}
  default {error "Unknown orientation $orient"}
 }
}
proc transform_rect {rect orient offset} {
 lassign $rect x0 y0 x1 y1;lassign $offset ox oy
 set xs {};set ys {}
 foreach p [list [list $x0 $y0] [list $x0 $y1] [list $x1 $y0] [list $x1 $y1]] {
  lassign [rotate {*}$p $orient] x y;lappend xs [expr {$x+$ox}];lappend ys [expr {$y+$oy}]
 }
 return [list [tcl::mathfunc::min {*}$xs] [tcl::mathfunc::min {*}$ys] [tcl::mathfunc::max {*}$xs] [tcl::mathfunc::max {*}$ys]]
}
set cache [dict create]
foreach inst [$b getInsts] {
 set master [$inst getMaster];set mn [$master getName]
 puts $f "[$inst getName]\t$mn\t[$master getType]"
 if {![dict exists $cache $mn]} {
  set obs {}
  foreach s [$master getObstructions] {
   set l [$s getTechLayer]
   if {$l ne "NULL" && [$l getRoutingLevel]>=4} {
    lappend obs [list [$l getName] [$s xMin] [$s yMin] [$s xMax] [$s yMax]]
   }
  }
  dict set cache $mn $obs
 }
 set obs [dict get $cache $mn];if {![llength $obs]} {continue}
 if {[$master getOrigin] ne "0 0"} {error "Nonzero master origin requires explicit qualification"}
 set t [$inst getTransform];set orient [$t getOrient];set offset [$t getOffset]
 set want [transform_rect [list 0 0 [$master getWidth] [$master getHeight]] $orient $offset]
 set bb [$inst getBBox];set got [list [$bb xMin] [$bb yMin] [$bb xMax] [$bb yMax]]
 if {$want ne $got} {error "Transform/bbox mismatch [$inst getName]: $want != $got"}
 foreach row $obs {
  set box [transform_rect [lrange $row 1 end] $orient $offset]
  puts $o "[lindex $row 0]\t[join $box \t]\t-1\tmacro_obs\t[$inst getName]"
 }
}
close $f
foreach ob [$b getObstructions] {
 set s [$ob getBBox];set l [$s getTechLayer]
 if {$l ne "NULL" && [$l getRoutingLevel]>=4} {puts $o "[$l getName]\t[$s xMin]\t[$s yMin]\t[$s xMax]\t[$s yMax]\t-1\tblock_obs\tBLOCK"}
}
close $o
puts "SUPPLEMENT_COMPLETE $::env(PINXY_CASE)"
