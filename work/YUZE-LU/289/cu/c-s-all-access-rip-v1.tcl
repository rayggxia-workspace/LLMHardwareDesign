# Rebuild retained S access after local ECO; preserve independently proved patches.
set sa_b [ord::get_db_block]
set sa_i [$sa_b findInst services.store.leaf]
if {$sa_i eq "NULL"} {error "Missing exact S macro"}
set sa_nets {}
foreach it [$sa_i getITerms] {
 set n [$it getNet]
 if {$n ne "NULL" && [$n getSigType] ni {POWER GROUND}} {dict set sa_nets [$n getName] $n}
}
set sa_f [open s-all-access-ripped.tsv w]
set sa_count 0;set sa_kept 0
foreach {name n} $sa_nets {
 set normalized [string map [list "\\" ""] $name]
 if {$normalized eq {dma_s_rsp_data[14]} || $normalized eq {dma_s_rsp_data[52]}} {incr sa_kept;puts $sa_f "$name\tkeep_proven_patch";continue}
 set w [$n getWire]
 if {$w ne "NULL"} {odb::dbWire_destroy $w;incr sa_count;puts $sa_f "$name\trip"}
}
close $sa_f
if {$sa_kept!=2} {error "Exact S patched nets scope changed"}
puts "C_S_ALL_ACCESS_RECOVERY nets=[dict size $sa_nets] ripped=$sa_count kept_patches=$sa_kept"
