# Exact half-open rectangle/window queries. Bins only prune; no shape is clipped.
namespace eval ::region {
  variable pitch 10000
  variable windows {}
  variable tiles {}
  variable aliases {}
  variable scanned 0
  variable emitted 0
  proc add {index x0 y0 x1 y1} {
    variable pitch;variable windows;variable tiles
    if {$x0 >= $x1 || $y0 >= $y1 || [dict exists $windows $index]} {error "Invalid or duplicate window"}
    dict set windows $index [list $x0 $y0 $x1 $y1]
    for {set x [expr {$x0/$pitch}]} {$x <= ($x1-1)/$pitch} {incr x} {
      for {set y [expr {$y0/$pitch}]} {$y <= ($y1-1)/$pitch} {incr y} {
        dict lappend tiles $x,$y $index
      }
    }
  }
  proc hits {x0 y0 x1 y1} {
    variable pitch;variable windows;variable tiles
    if {$x0 >= $x1 || $y0 >= $y1} {error "Degenerate query"}
    set seen {};set result {}
    for {set x [expr {$x0/$pitch}]} {$x <= ($x1-1)/$pitch} {incr x} {
      for {set y [expr {$y0/$pitch}]} {$y <= ($y1-1)/$pitch} {incr y} {
        if {![dict exists $tiles $x,$y]} {continue}
        foreach i [dict get $tiles $x,$y] {
          if {[dict exists $seen $i]} {continue}
          dict set seen $i 1
          lassign [dict get $windows $i] a b c d
          if {$x0 < $c && $a < $x1 && $y0 < $d && $b < $y1} {lappend result $i}
        }
      }
    }
    return $result
  }
}
