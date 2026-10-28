# Independent selected-net connectivity export. All layers, real dbWire/vias and
# actual ITerm access rectangles; no bbox-center connectivity approximation.
set block [ord::get_db_block];set selected [dict create]
if {[info exists ::env(PINXY_ACCESS_ALL)] && $::env(PINXY_ACCESS_ALL) eq "1"} {
  foreach n [$block getNets] {if {[$n getSigType] ni {POWER GROUND} && [llength [$n getITerms]]+[llength [$n getBTerms]]>1} {dict set selected [$n getId] $n}}
} else {
  set relocations {};source $::env(PINXY_RELOCATIONS)
  foreach r $relocations {set t [$block findBTerm [lindex $r 0]];set n [$t getNet];dict set selected [$n getId] $n}
}
if {[file exists $::env(PINXY_ACCESS_OUT)]} {error "Do not overwrite existing access export"}
if {[file extension $::env(PINXY_ACCESS_OUT)] eq ".gz"} {set af [open [list | gzip -n -c > $::env(PINXY_ACCESS_OUT)] w]} else {set af [open $::env(PINXY_ACCESS_OUT) w]}
puts $af "net\tlayer\tx0\ty0\tx1\ty1\tkind\tlink"
proc access_row {nn layer bb kind link} {
  global af
  puts $af [join [list $nn $layer {*}$bb $kind $link] "\t"]
}
proc access_box {nn s kind link {dx 0} {dy 0}} {
  set layer [$s getTechLayer]
  if {$layer eq "NULL"} {error "Missing layer"}
  access_row $nn [$layer getName] [list [expr {[$s xMin]+$dx}] [expr {[$s yMin]+$dy}] [expr {[$s xMax]+$dx}] [expr {[$s yMax]+$dy}]] $kind $link
}
set itr [odb::dbWirePathItr];set path [odb::dbWirePath];set ps [odb::dbWirePathShape]
dict for {nid net} $selected {
  set nn [$net getName];set w [$net getWire];set serial 0
  if {[llength [$net getSWires]]} {error "Signal special-wire geometry requires explicit extension: $nn"}
  if {$w eq "NULL"} {
    access_row $nn UNROUTED {0 0 0 0} UNROUTED MISSING_WIRE
  } else {
   $itr begin $w
   while {[$itr getNextPath $path]} {while {[$itr getNextShape $ps]} {
    incr serial;set s [odb::dbWirePathShape_shape_get $ps]
    if {[$s isVia]} {
      set v [$s getTechVia];if {$v eq "NULL"} {set v [$s getVia]};lassign [$s getViaXY] x y
      foreach box [$v getBoxes] {access_box $nn $box VIA "via_$serial" $x $y}
    } else {access_box $nn $s WIRE "wire_$serial"}
   }}
  }
  foreach bt [$net getBTerms] {
    set count 0
    foreach bp [$bt getBPins] {foreach box [$bp getBoxes] {incr count;access_box $nn $box BTERM "B:[$bt getName]"}}
    if {!$count} {error "No real access rectangles B:[$bt getName]"}
  }
  foreach it [$net getITerms] {
    set boxes [$it getGeometries];set term "I:[[$it getInst] getName]/[[$it getMTerm] getName]"
    if {![llength $boxes]} {error "No real access rectangles $term"}
    set xs {};set ys {}
    foreach g $boxes {
      set layer [lindex $g 0];set r [lindex $g 1]
      set bb [list [$r xMin] [$r yMin] [$r xMax] [$r yMax]]
      lappend xs [$r xMin] [$r xMax];lappend ys [$r yMin] [$r yMax]
      access_row $nn [$layer getName] $bb ITERM $term
    }
    set want [list [tcl::mathfunc::min {*}$xs] [tcl::mathfunc::min {*}$ys] [tcl::mathfunc::max {*}$xs] [tcl::mathfunc::max {*}$ys]]
    set r [$it getBBox];set got [list [$r xMin] [$r yMin] [$r xMax] [$r yMax]]
    if {$want ne $got} {error "ITerm access coordinate/bbox mismatch $term: $want != $got"}
  }
}
close $af
puts "SELECTED_ACCESS_EXPORTED [dict size $selected] nets"
