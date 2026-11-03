# The complete original GDS deck found the one remaining long clock-input
# M9 antenna in082. Move the existing root, not add clock logic or change SDC.
set originals {}
set term [$block findBTerm clk];set rootpins [[$term getNet] getITerms]
if {[llength $rootpins]!=1} {error "Unexpected clock root fanout"}
set pin [lindex $rootpins 0];set root [$pin getInst];set rootmaster [[$root getMaster] getName]
if {[[$pin getMTerm] getName] ne "A" || $rootmaster ni {BUF_X8 BUF_X16}} {error "Unexpected actual clock root: $rootmaster"}
set rootname [$root getName];set rootnet [[$term getNet] getName]
foreach inst [$block getInsts] {
 lappend originals [list [$inst getName] [$inst getPlacementStatus] [$inst getLocation] [$inst getOrient]]
 $inst setPlacementStatus LOCKED
}
set boxes {};foreach bp [$term getBPins] {foreach box [$bp getBoxes] {lappend boxes $box}}
if {[llength $boxes]!=1} {error "Nonunique clock pin"}
set box [lindex $boxes 0]
if {[[$box getTechLayer] getName] ne "metal10"} {error "Clock pin layer changed"}
set px [expr {([$box xMin]+[$box xMax])/2.0}];set py [expr {([$box yMin]+[$box yMax])/2.0}]
lassign [$root getLocation] ox oy
set dx [expr {$ox-$px}];set dy [expr {$oy-$py}]
set tx $px;set ty $py
set offset [expr {$rootmaster eq "BUF_X8"?32:64}]
if {abs($dx)>=abs($dy)} {set tx [expr {$px+($dx>=0?1:-1)*$offset*$dbu}]} else {set ty [expr {$py+($dy>=0?1:-1)*$offset*$dbu}]}
foreach region [$block getRegions] {
 foreach boundary [$region getBoundaries] {
  if {$tx>=[$boundary xMin] && $tx<[$boundary xMax] && $ty>=[$boundary yMin] && $ty<[$boundary yMax]} {
   $region addInst $root;[$block findGroup "[$region getName]_cells"] addInst $root
  }
 }
}
$root setPlacementStatus PLACED
$root setLocation [expr {round($tx)}] [expr {round($ty)}]
detailed_placement -max_displacement {10 10}
check_placement -verbose
foreach row $originals {
 lassign $row name status location orient;set inst [$block findInst $name]
 if {$name ne $rootname && ([$inst getLocation] ne $location || [$inst getOrient] ne $orient)} {error "Unrelated cell moved during clock root repair"}
 $inst setPlacementStatus $status
}
lassign [$root getLocation] nx ny
set distance [expr {(abs($nx-$px)+abs($ny-$py))/double($dbu)}]
if {$distance>100 || [[$term getNet] getName] ne $rootnet || [llength [[$term getNet] getITerms]]!=1} {error "Clock root repair invalid"}
$root setPlacementStatus LOCKED
set_dont_touch [get_cells [list $rootname]]
set f [open $here/CLOCK_ROOT_AUDIT.tsv w]
puts $f "root\tmaster\told_x_um\told_y_um\tnew_x_um\tnew_y_um\tpin_x_um\tpin_y_um\tmanhattan_um"
puts $f "$rootname\t$rootmaster\t[expr {$ox/double($dbu)}]\t[expr {$oy/double($dbu)}]\t[expr {$nx/double($dbu)}]\t[expr {$ny/double($dbu)}]\t[expr {$px/double($dbu)}]\t[expr {$py/double($dbu)}]\t$distance"
close $f
puts "R166_CLOCK_ROOT_SHORT_INPUT=$rootname; input_distance_um=$distance; existing_clock_logic_unchanged=1"
