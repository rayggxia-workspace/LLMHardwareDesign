# Append real patch wires, preserving every existing routed shape and net.
# Runs after detailed routing, before final DEF/GDS and RCX generation.
set block [ord::get_db_block]
set layer [[ord::get_db_tech] findLayer metal3]
set stream [open $::env(RESULTS_DIR)/sram-landing-patches.tsv w]
set count 0
foreach bank [$block getInsts] {
  if {[[$bank getMaster] getName] ne "s_sram_256x128_freepdk45"} {continue}
  if {[$bank getOrient] ne "R0"} {error "Landing repair requires checked R0 bank placement"}
  lassign [$bank getLocation] bx by
  foreach patch $sram_landing_patches {
    lassign $patch pin x1 y1 x2 y2
    set term [$bank findITerm $pin]
    if {$term eq "NULL" || [$term getNet] eq "NULL"} {error "Missing real SRAM landing net"}
    set net [$term getNet]
    set wire [$net getWire]
    if {$wire eq "NULL"} {error "SRAM landing net not routed"}
    set x [expr {$bx+($x1+$x2)/2}]
    set y [expr {$by+($y1+$y2)/2}]
    set encoder [odb::dbWireEncoder]
    $encoder append $wire
    $encoder newPath $layer ROUTED
    $encoder addPoint $x $y
    $encoder addRect [expr {$bx+$x1-$x}] [expr {$by+$y1-$y}] [expr {$bx+$x2-$x}] [expr {$by+$y2-$y}]
    $encoder addITerm $term
    $encoder end
    odb::delete_dbWireEncoder $encoder
    puts $stream "[$bank getName]\t$pin\t[$net getName]\t[expr {$bx+$x1}]\t[expr {$by+$y1}]\t[expr {$bx+$x2}]\t[expr {$by+$y2}]"
    incr count
  }
}
close $stream
if {$count != 1068} {error "Expected 4*267 real landing patches; got $count"}
