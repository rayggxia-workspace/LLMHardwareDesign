rename bvgeom::rectangle bvgeom::unfiltered_rectangle
proc bvgeom::rectangle {stream net layer kind object {dx 0} {dy 0} {transform ""}} {
  set x0 [expr {[$object xMin]+$dx}]
  set y0 [expr {[$object yMin]+$dy}]
  set x1 [expr {[$object xMax]+$dx}]
  set y1 [expr {[$object yMax]+$dy}]
  if {[present $transform]} {
    set xs {}; set ys {}
    foreach x [list $x0 $x1] {
      foreach y [list $y0 $y1] {
        set point [odb::new_Point $x $y]
        $transform apply $point
        lappend xs [$point getX]; lappend ys [$point getY]
        odb::delete_Point $point
      }
    }
    set x0 [tcl::mathfunc::min {*}$xs]; set x1 [tcl::mathfunc::max {*}$xs]
    set y0 [tcl::mathfunc::min {*}$ys]; set y1 [tcl::mathfunc::max {*}$ys]
  }
  if {$x0 >= $x1 || $y0 >= $y1} { error "Degenerate conductor rectangle" }
  variable markers; variable hits
  set name [$layer getName]
  if {![dict exists $markers $name]} {return}
  foreach marker [dict get $markers $name] {
    lassign $marker index mx0 my0 mx1 my1
    if {$x0 < $mx1 && $mx0 < $x1 && $y0 < $my1 && $my0 < $y1} {
      puts $stream "$index	$net	$name	$kind	$x0	$y0	$x1	$y1"
      incr hits
    }
  }
}

set block [ord::get_db_block]
if {[$block getDbUnitsPerMicron]!=2000} {error "Unexpected DBU"}
set f [open marker-cells.tsv w]
set metadata [open cell-identities.tsv w]
set bvgeom::hits 0;set instances 0;set selected 0;set pins 0;set obs 0
foreach inst [$block getInsts] {
  incr instances
  set bb [$inst getBBox];set use 0
  foreach layer [dict keys $bvgeom::markers] {
    foreach marker [dict get $bvgeom::markers $layer] {
      lassign $marker index mx0 my0 mx1 my1
      if {[$bb xMin]<$mx1 && $mx0<[$bb xMax] && [$bb yMin]<$my1 && $my0<[$bb yMax]} {set use 1}
    }
  }
  if {!$use} {continue}
  incr selected;set transform [$inst getTransform];set master [$inst getMaster]
  puts $metadata "i[$inst getId]\t[binary encode hex [$inst getName]]\t[binary encode hex [$master getName]]\t[$inst getOrient]\t[$bb xMin]\t[$bb yMin]\t[$bb xMax]\t[$bb yMax]"
  foreach term [$inst getITerms] {
    set net [$term getNet];set alias unconnected
    if {[bvgeom::present $net]} {set alias [binary encode hex [encoding convertto utf-8 [$net getName]]]}
    set kind instance-pin-i[$inst getId]-[binary encode hex [[$term getMTerm] getName]]
    foreach pin [[$term getMTerm] getMPins] {
      foreach box [$pin getGeometry] {incr pins;bvgeom::db_box $f $alias $box $kind $transform}
    }
  }
  foreach box [$master getObstructions] {incr obs;bvgeom::db_box $f i[$inst getId] $box instance-obstruction $transform}
}
close $f;close $metadata
set f [open scan-counts.tsv w];puts $f "$instances\t$selected\t$pins\t$obs\t$bvgeom::hits";close $f
