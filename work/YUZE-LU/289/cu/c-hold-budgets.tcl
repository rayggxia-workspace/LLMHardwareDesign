source /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/c-remaining-cts.tcl
source /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/c-v17-hold-targets.tcl
set pins [dict create]
foreach pin [all_registers -data_pins] {
 set name [string map [list "\\" ""] [get_full_name $pin]]
 set cell [string range $name 0 [expr {[string last / $name]-1}]]
 dict set pins $cell $pin
}
set f [open $::env(CU_OUT)/hold-setup-budgets.tsv w]
puts $f "endpoint\thold_slack_ns\tsetup_slack_ns\tproposed_cells\tallowed"
foreach target $targets {
 lassign $target name hslack
 set name [string map [list "\\" ""] $name]
 if {![dict exists $pins $name]} {error "Missing exact data pin $name"}
 set pin [dict get $pins $name]
 set paths [find_timing_paths -to $pin -path_delay max -group_path_count 1]
 if {[llength $paths]!=1} {error "Missing max path to $name"}
 set setup [get_property [lindex $paths 0] slack]
 set n [expr {int(ceil((-$hslack+0.07)/0.025))}]
 set allowed [expr {$setup > $n*0.04+0.08}]
 puts $f "$name\t$hslack\t$setup\t$n\t$allowed"
}
close $f