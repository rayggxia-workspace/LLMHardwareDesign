read_db {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/common_checkpoint_def_import/r01/imported_current_NOT_ROUTED_NOT_FROZEN.odb}

set b [ord::get_db_block];set i [$b findInst u_llaccel_aux]
if {$i eq "NULL" || [$i getOrient] ne "R0"} {error "Expected original R0 LL placement missing"}
lassign [$i getLocation] ix iy;set bb [$i getBBox];set maxx [expr {[$bb xMax]-$ix+20000}];set maxy [expr {[$bb yMax]-$iy+20000}]
set f [open {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/parent_pg_llsys_local/r01/actual_parent_PG_local.tsv} w];puts $f "net\tlayer\tx0\ty0\tx1\ty1\tkind"
proc emit {f net layer a c d e ix iy maxx maxy} {
 if {$layer ni {metal5 metal6 metal7 via5 via6}} {return}
 set a [expr {$a-$ix}];set c [expr {$c-$iy}];set d [expr {$d-$ix}];set e [expr {$e-$iy}]
 if {$a>$maxx || $c>$maxy || $d< -20000 || $e< -20000} {return}
 puts $f [join [list $net $layer $a $c $d $e PARENT_PG] "\t"]
}
foreach n [$b getNets] {
 if {[$n getSigType] ni {POWER GROUND}} {continue}
 foreach sw [$n getSWires] {foreach s [$sw getWires] {
  if {[$s isVia]} {
   set via [$s getTechVia];if {$via eq "NULL"} {set via [$s getBlockVia]};lassign [$s getViaXY] x y
   foreach z [$via getBoxes] {emit $f [$n getName] [[$z getTechLayer] getName] [expr {$x+[$z xMin]}] [expr {$y+[$z yMin]}] [expr {$x+[$z xMax]}] [expr {$y+[$z yMax]}] $ix $iy $maxx $maxy}
  } else {emit $f [$n getName] [[$s getTechLayer] getName] [$s xMin] [$s yMin] [$s xMax] [$s yMax] $ix $iy $maxx $maxy}
 }}
};close $f
set f [open {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/parent_pg_llsys_local/r01/actual_transform.tsv} w];puts $f [list R0 $ix $iy [$bb xMin] [$bb yMin] [$bb xMax] [$bb yMax] [$b getDbUnitsPerMicron]];close $f
help pin_access
if {[llength [info commands pin_access]]} {set f [open {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/parent_pg_llsys_local/r01/native_pin_access_body.txt} w];puts $f [info body pin_access];close $f}

