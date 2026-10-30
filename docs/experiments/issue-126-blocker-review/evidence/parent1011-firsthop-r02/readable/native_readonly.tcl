read_db {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/llsys_wire_pin_retention/r01/routed.odb}
set b [ord::get_db_block];set seen [dict create]
foreach inst [$b getInsts] {set m [$inst getMaster];dict set seen [$m getName] $m}
set f [open {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/llsys_parent_failed_pin_preflight/r02/actual_used_master_high_layers.tsv} w];puts $f "master\ttype\thighest_routing_geometry_level"
dict for {name m} $seen {
 set high 0;foreach z [$m getObstructions] {set high [expr {max($high,[[$z getTechLayer] getRoutingLevel])}]}
 foreach mt [$m getMTerms] {foreach p [$mt getMPins] {foreach z [$p getGeometry] {set high [expr {max($high,[[$z getTechLayer] getRoutingLevel])}]}}}
 puts $f [join [list $name [$m getType] $high] "\t"]
 if {$high>=5 || [$m getType] eq "BLOCK"} {error "Real high-layer master geometry needs explicit transformed export; never assume it empty"}
};close $f
set f [open {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/llsys_parent_failed_pin_preflight/r02/all87_actual_peers.tsv} w];puts $f "pin\tnet\tinstance\tmaster\tinstance_pin"
foreach name {{bit_1011}} {set bt [$b findBTerm $name];set n [$bt getNet];if {[llength [$n getBTerms]]!=1 || [llength [$n getITerms]]!=1} {error "Residual real endpoint contract changed"};set it [lindex [$n getITerms] 0];set i [$it getInst];puts $f [join [list $name [$n getName] [$i getName] [[$i getMaster] getName] [[$it getMTerm] getName]] "\t"]};close $f
set ::env(PINXY_ACCESS_OUT) {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/llsys_parent_failed_pin_preflight/r02/actual_high_PG_OBS.tsv}
set pf [open {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/llsys_parent_failed_pin_preflight/r02/actual_high_PG_OBS.tsv} w];puts $pf "net\tlayer\tx0\ty0\tx1\ty1\tkind\tlink"
foreach n [$b getNets] {if {[$n getSigType] ni {POWER GROUND}} {continue};foreach sw [$n getSWires] {foreach z [$sw getWires] {
 if {[$z isVia]} {set v [$z getTechVia];if {$v eq "NULL"} {set v [$z getBlockVia]};lassign [$z getViaXY] x y;foreach a [$v getBoxes] {set layer [[$a getTechLayer] getName];if {$layer in {metal5 metal6 metal7 via5 via6}} {puts $pf [join [list [$n getName] $layer [expr {$x+[$a xMin]}] [expr {$y+[$a yMin]}] [expr {$x+[$a xMax]}] [expr {$y+[$a yMax]}] PG_VIA {}] "\t"]}}} else {set layer [[$z getTechLayer] getName];if {$layer in {metal5 metal6 metal7}} {puts $pf [join [list [$n getName] $layer [$z xMin] [$z yMin] [$z xMax] [$z yMax] PG_WIRE {}] "\t"]}}
}}}
foreach ob [$b getObstructions] {set z [$ob getBBox];set layer [[$z getTechLayer] getName];if {$layer in {metal5 metal6 metal7 via5 via6}} {puts $pf [join [list __BLOCK_OBS__ $layer [$z xMin] [$z yMin] [$z xMax] [$z yMax] OBS {}] "\t"]}};close $pf
set f [open {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/llsys_parent_failed_pin_preflight/r02/actual_first_hop_vias.tsv} w];puts $f "via\tlayer\tx0\ty0\tx1\ty1"
foreach name {via5_0 via6_0} {set v [[ord::get_db_tech] findVia $name];if {$v eq "NULL"} {error "Actual original first-hop via missing"};foreach z [$v getBoxes] {puts $f [join [list $name [[$z getTechLayer] getName] [$z xMin] [$z yMin] [$z xMax] [$z yMax]] "\t"]}};close $f
set r [$b getDieArea];set f [open {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/llsys_parent_failed_pin_preflight/r02/actual_die.tsv} w];puts $f [list [$r xMin] [$r yMin] [$r xMax] [$r yMax]];close $f
