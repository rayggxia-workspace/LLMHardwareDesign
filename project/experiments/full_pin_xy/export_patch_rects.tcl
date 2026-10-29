# Additive RECT/patch inventory via installed native APIs; no physical edits.
# Raw opcode 14 and three OPERAND 11 bytes are accepted only when their count
# and order independently match native dbWireDecoder_RECT events on each wire.
set pxy_block [ord::get_db_block];set pxy_nets {}
if {[info exists ::env(PINXY_PATCH_NET_NAMES)]} {
 foreach name $::env(PINXY_PATCH_NET_NAMES) {set n [$pxy_block findNet $name];if {$n eq "NULL"} {error "Missing patch inventory net $name"};lappend pxy_nets $n}
} else {set pxy_nets [$pxy_block getNets]}
if {[file exists $::env(PINXY_PATCH_OUT)] || [file exists $::env(PINXY_PATCH_COUNTS)]} {error "Patch inventory output already exists"}
set pxy_f [open $::env(PINXY_PATCH_OUT) w];puts $pxy_f "net\tlayer\tx0\ty0\tx1\ty1\tkind\tlink"
set pxy_counts [dict create examined_nets 0 native_wires 0 native_decoder_RECT 0 exported_patch_rectangles 0 signal_special_wire_nets_not_audited 0]
set pxy_d [odb::dbWireDecoder]
foreach n $pxy_nets {
 dict incr pxy_counts examined_nets
 if {[llength [$n getSWires]] && [$n getSigType] ni {POWER GROUND}} {dict incr pxy_counts signal_special_wire_nets_not_audited}
 set w [$n getWire];if {$w eq "NULL"} {continue};dict incr pxy_counts native_wires
 set raw_rects {};set count [$w length]
 for {set i 0} {$i<$count} {incr i} {
  if {[$w getOpcode $i]!=14} {continue}
  if {$i+3>=$count} {error "Incomplete RECT operands on [$n getName]"}
  foreach j [list [expr {$i+1}] [expr {$i+2}] [expr {$i+3}]] {if {[$w getOpcode $j]!=11} {error "Unsupported RECT operand encoding"}}
  lappend raw_rects $i
 }
 set rect_index 0;$pxy_d begin $w
 while {1} {
  set op [$pxy_d next];if {$op==$::odb::dbWireDecoder_END_DECODE} {break}
  if {$op!=$::odb::dbWireDecoder_RECT} {continue}
  dict incr pxy_counts native_decoder_RECT
  if {$rect_index>=[llength $raw_rects]} {error "Native RECT not represented by verified raw opcode; do not silently omit it"}
  set i [lindex $raw_rects $rect_index];incr rect_index
  lassign [$w getCoord $i] x y
  set l [$pxy_d getLayer];if {$l eq "NULL"} {error "Missing native RECT layer"}
  set bb [list [expr {$x+[$w getData $i]}] [expr {$y+[$w getData [expr {$i+1}]]}] [expr {$x+[$w getData [expr {$i+2}]]}] [expr {$y+[$w getData [expr {$i+3}]]}]]
  lassign $bb x0 y0 x1 y1
  if {$x0>$x1 || $y0>$y1} {error "Reversed native RECT extents"}
  puts $pxy_f [join [list [$n getName] [$l getName] {*}$bb PATCH patch_opcode_$i] "\t"]
  dict incr pxy_counts exported_patch_rectangles
 }
 if {$rect_index!=[llength $raw_rects]} {error "Raw RECT/native decoder inventory disagreement"}
}
close $pxy_f
set pxy_c [open $::env(PINXY_PATCH_COUNTS) w];dict for {k v} $pxy_counts {puts $pxy_c "$k\t$v"};close $pxy_c
puts "NATIVE_PATCH_RECT_INVENTORY $pxy_counts"
