# Virtual routing obstruction in the actual empty gap; no physical metal edit.
namespace eval ::c_s_m9_guard {
set block [::ord::get_db_block]
set tech [[::ord::get_db] getTech]
if {[$tech getDbUnitsPerMicron]!=2000} {error "Unexpected DBU"}
set layer [$tech findLayer metal9]
set n [$block findNet net52834]
if {$n eq "NULL" || [llength [$n getBTerms]]!=0} {error "Expected internal net52834"}
set macro [$block findInst services.store.leaf]
if {$macro eq "NULL"} {error "Missing fixed S macro"}
set rect {2722800 223340 2723000 224940}
set found 0
foreach ob [$block getObstructions] {
 set bb [$ob getBBox]
 if {[[$bb getTechLayer] getName] eq "metal9" && [list [$bb xMin] [$bb yMin] [$bb xMax] [$bb yMax]] eq $rect} {set found 1}
}
set added 0
if {!$found} {lassign $rect x1 y1 x2 y2;::odb::dbObstruction_create $block $layer $x1 $y1 $x2 $y2;set added 1}
set ripped 0
if {[$n getWire] ne "NULL"} {::odb::dbWire_destroy [$n getWire];set ripped 1}
puts "C_S_M9_GUARD added=$added ripped=$ripped"
}
