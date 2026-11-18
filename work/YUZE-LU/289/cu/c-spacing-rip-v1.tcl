# Rip mapped actual upper-rule conflict nets, retaining the frozen52 notch repair
# if its endpoints/cells have not otherwise changed in the preceding ECO stage.
set sr_b [ord::get_db_block]
set sr_lookup {}
foreach n [$sr_b getNets] {
 set k [string map [list "\\" ""] [$n getName]]
 if {[dict exists $sr_lookup $k]} {error "Ambiguous normalized net $k"}
 dict set sr_lookup $k $n
}
set sr_f [open $::env(C_SPACING_RIP_LIST)]
set sr_out [open spacing-route-rip.tsv w]
while {[gets $sr_f raw]>=0} {
 if {[string trim $raw] eq ""} {continue}
 set key [string map [list "\\" ""] $raw]
 if {$key eq {dma_s_rsp_data[52]}} {puts $sr_out "$raw\tkeep_proven_notch_if_wire_unchanged";continue}
 if {![dict exists $sr_lookup $key]} {puts $sr_out "$raw\tremoved_by_electrical_edit";continue}
 set n [dict get $sr_lookup $key]
 if {[$n getSigType] in {POWER GROUND}} {error "Unexpected PG conflict net"}
 set w [$n getWire]
 if {$w ne "NULL"} {odb::dbWire_destroy $w;puts $sr_out "$raw\trip_existing_wire"} else {puts $sr_out "$raw\talready_unrouted"}
}
close $sr_f;close $sr_out
