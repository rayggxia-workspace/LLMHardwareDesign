# Plan from global RC. Buffer-delay constants only size this trial.
# Final timing is measured again after legalization and rerouting.
set instances {}
foreach instance [$block getInsts] {
    dict set instances [string map [list "\\" ""] [$instance getName]] $instance
}
set records {}
foreach path [find_timing_paths -path_delay min -slack_max 0 -group_path_count 10000 -endpoint_path_count 1] {
    lappend records [list [get_property $path endpoint] [get_property $path slack]]
}
set plan {}
set seen {}
set budget [open targeted-delay-budget.tsv w]
puts $budget "endpoint\thold_ns\tsetup_ns\trequested_cells\tchosen_cells\tstatus"
foreach record $records {
    lassign $record pin hold_slack
    set name [string map [list "\\" ""] [get_full_name $pin]]
    if {[dict exists $seen $name]} {continue}
    dict set seen $name 1
    set slash [string last / $name]
    set instance_name [string range $name 0 [expr {$slash-1}]]
    set terminal [string range $name [expr {$slash+1}] end]
    if {$slash < 0 || $terminal ne "D" || ![dict exists $instances $instance_name]} {
        puts $budget "$name\t$hold_slack\tNA\t0\t0\tseparate_endpoint_review"
        continue
    }
    set instance [dict get $instances $instance_name]
    if {![string match DFF* [[$instance getMaster] getName]]} {
        error "Expected ordinary DFF data sink $name"
    }
    set max_paths [find_timing_paths -to $pin -path_delay max -group_path_count 1]
    if {[llength $max_paths] != 1} {error "Missing setup budget $name"}
    set setup_slack [get_property [lindex $max_paths 0] slack]
    set requested [expr {int(ceil((-$hold_slack+.030)/.025))}]
    set available [expr {int(floor(($setup_slack-.010)/.040))}]
    set chosen [expr {max(0,min($requested,$available))}]
    puts $budget "$name\t$hold_slack\t$setup_slack\t$requested\t$chosen\tplanned"
    if {$chosen > 0} {lappend plan [list [$instance findITerm D] $chosen]}
}
close $budget

proc insert_delay_chain {sink count prefix} {
    set block [ord::get_db_block]
    set previous [$sink getNet]
    if {$previous eq "NULL" || [$previous getSigType] in {POWER GROUND CLOCK}} {
        error "Invalid data/reset delay branch $prefix"
    }
    lassign [[$sink getInst] getLocation] x y
    set master [[ord::get_db] findMaster CLKBUF_X1]
    $sink disconnect
    for {set n 0} {$n < $count} {incr n} {
        set name ${prefix}_$n
        if {[$block findInst $name] ne "NULL"} {error "Delay instance already exists $name"}
        set instance [odb::dbInst_create $block $master $name]
        $instance setLocation $x $y
        $instance setPlacementStatus PLACED
        set net [odb::dbNet_create $block ${name}_net]
        [$instance findITerm A] connect $previous
        [$instance findITerm Z] connect $net
        set_dont_touch [get_cells [list $name]]
        set previous $net
    }
    $sink connect $previous
}

set serial 0
foreach entry $plan {
    lassign $entry sink count
    insert_delay_chain $sink $count i289_grthold_$::env(C_REPAIR_TAG)_$serial
    incr serial
}
set reset [$block findInst input1249]
if {$reset eq "NULL" || [$reset findITerm A] eq "NULL"} {error "Missing exact reset branch"}
insert_delay_chain [$reset findITerm A] $::env(C_REPAIR_RESET_COUNT) i289_grtreset_$::env(C_REPAIR_TAG)
puts "TARGETED_DATA_BRANCHES_DELAYED $serial RESET_CELLS $::env(C_REPAIR_RESET_COUNT)"
