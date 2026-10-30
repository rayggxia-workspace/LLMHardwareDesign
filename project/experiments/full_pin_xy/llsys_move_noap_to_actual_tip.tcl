# Actual bit_1025 source native0/r02, diagnosed by native read-only context/r01.
# Same-net via5_0 at (706910,2129260) DBU already exists. Preserve its definition,
# location and all remaining routed rectangles; remove exactly three old stubs.
set specs {{bit_1025 metal5 {707700 2128980 707980 2129260} {706770 2129120 707050 2129400} wire54795 A 167}}
set removed [dict create bit_1025 {{metal5 707330 2128980 707750 2129260} {metal5 707330 2128980 707610 2129400} {metal5 706770 2129120 707610 2129400}}]
source [file join [file dirname [info script]] llsys_move_to_actual_via_tips.tcl]
