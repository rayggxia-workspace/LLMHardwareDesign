# Regenerate all hard-macro signal/clock route access after importing existing routes.
# Geometry, logic, pins, and proven S14/52 material remain untouched.
set ma_b [ord::get_db_block]
set ma_nets {};set ma_macros 0
foreach ma_i [$ma_b getInsts] {
 if {![[$ma_i getMaster] isBlock]} {continue}
 incr ma_macros
 foreach ma_it [$ma_i getITerms] {
  set ma_n [$ma_it getNet]
  if {$ma_n ne "NULL" && [$ma_n getSigType] ni {POWER GROUND}} {dict set ma_nets [$ma_n getName] $ma_n}
 }
}
if {$ma_macros!=5} {error "Actual macro count changed"}
set ma_f [open all-macro-access-ripped.tsv w]
set ma_count 0;set ma_kept 0
foreach {ma_name ma_n} $ma_nets {
 set ma_normalized [string map [list "\\" ""] $ma_name]
 if {$ma_normalized eq {dma_s_rsp_data[14]} || $ma_normalized eq {dma_s_rsp_data[52]}} {incr ma_kept;puts $ma_f "$ma_name\tkeep_proven_patch";continue}
 set ma_w [$ma_n getWire]
 if {$ma_w ne "NULL"} {odb::dbWire_destroy $ma_w;incr ma_count;puts $ma_f "$ma_name\trip"} else {puts $ma_f "$ma_name\talready_unrouted"}
}
close $ma_f
if {$ma_kept!=2} {error "Patched nets changed"}
puts "C_ALL_MACRO_ACCESS_RECOVERY macros=$ma_macros nets=[dict size $ma_nets] ripped=$ma_count kept=$ma_kept"
