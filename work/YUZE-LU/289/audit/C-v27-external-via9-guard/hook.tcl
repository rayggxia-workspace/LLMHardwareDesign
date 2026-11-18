# Virtual via9 routing keepouts only. No physical metal or BPin edit.
namespace eval ::c_external_via9_guard {
set package [file dirname [file normalize [info script]]]
set block [::ord::get_db_block]
set tech [[::ord::get_db] getTech]
if {[$tech getDbUnitsPerMicron]!=2000} {error "Unexpected DBU"}
set layer [$tech findLayer via9]
if {$layer eq "NULL"} {error "via9 missing"}
set f [open $package/expected-bpins.tsv];set nets {};set expected {}
while {[gets $f line]>=0} {
 set a [split $line "\t"];lassign $a port netname ln x1 y1 x2 y2
 set bt [$block findBTerm $port]
 if {$bt eq "NULL" || [[$bt getNet] getName] ne $netname} {error "Expected port/net changed $port"}
 set actual {}
 foreach bp [$bt getBPins] {foreach box [$bp getBoxes] {lappend actual [list $port $netname [[$box getTechLayer] getName] [$box xMin] [$box yMin] [$box xMax] [$box yMax]]}}
 if {$actual ne [list $a]} {error "Expected exact port geometry changed $port"}
 dict set nets $netname [$bt getNet]
 lappend expected $a
}
close $f
if {[dict size $nets]!=4} {error "Expected four nets"}
set rectangles {{1953690 2348140 1953890 2349740} {3124890 2348140 3125090 2349740}}
set present {}
foreach ob [$block getObstructions] {set box [$ob getBBox];dict set present [list [[$box getTechLayer] getName] [$box xMin] [$box yMin] [$box xMax] [$box yMax]] 1}
set added 0
foreach rect $rectangles {
 set key [linsert $rect 0 via9]
 if {[dict exists $present $key]} {continue}
 lassign $rect x1 y1 x2 y2
 ::odb::dbObstruction_create $block $layer $x1 $y1 $x2 $y2
 incr added
}
set f [open external-via9-ripped.tsv a];set ripped 0
foreach name [dict keys $nets] {set net [dict get $nets $name];if {[$net getWire] ne "NULL"} {::odb::dbWire_destroy [$net getWire];puts $f $name;incr ripped}}
close $f
puts "C_EXTERNAL_VIA9_VIRTUAL_GUARD added=$added ripped=$ripped"
}
