# Audit independently sourced fixture cuts against actual joint cell terminals.
set_thread_count $::env(SLURM_CPUS_PER_TASK)
read_db $::env(INPUT_DB)
set block [ord::get_db_block]
set db [ord::get_db]
set all_cuts {}
set in [open $::env(FUNCTION_ENDPOINTS) r]
while {[gets $in line]>=0} {
    lassign [split $line "\t"] id group candidate role inst pin
    dict lappend all_cuts $id [list $group $candidate $role $inst $pin]
}
close $in
set report [open function-cut-audit.tsv w]
puts $report "cut\tgroup\tcandidate\tstatus\tdetail"
set identities [open function-cut-identity.tsv w]
puts $identities "cut\tleg\trole\tnative_net\tanchor_class\ttargets"
set tally {}
set claimed {}
foreach id [dict keys $all_cuts] {
    set expected {}
    set problem {}
    set nets {}
    foreach item [dict get $all_cuts $id] {
        lassign $item group candidate role name pin
        set inst [$block findInst $name]
        if {$inst eq "NULL"} {
            set escaped [string map [list {[} {\[} {]} {\]}] $name]
            set inst [$block findInst $escaped]
        }
        if {$inst eq "NULL"} {lappend problem "no_instance:$name"; continue}
        set iterm [$inst findITerm $pin]
        if {$iterm eq "NULL"} {lappend problem "no_pin:$name/$pin"; continue}
        set direction [[$iterm getMTerm] getIoType]
        if {($role eq "driver" && $direction ne "OUTPUT") ||
            ($role eq "receiver" && $direction ne "INPUT")} {
            lappend problem "wrong_direction:$name/$pin/$direction"
            continue
        }
        set net [$iterm getNet]
        if {$net eq "NULL" || [$net getSigType] ne "SIGNAL" || [$net getWire] ne "NULL"} {
            lappend problem "unavailable_unrouted_signal:$name/$pin"
            continue
        }
        dict set expected $iterm $role
        dict set nets $net [$net getName]
    }
    set maintenance_loads 0
    set retained_service_aliases {}
    set sources {}
    set sinks {}
    dict for {net name} $nets {
        set found_drivers 0
        foreach iterm [$net getITerms] {
            set role [[$iterm getMTerm] getIoType]
            if {$role eq "OUTPUT"} {incr found_drivers}
            if {![dict exists $expected $iterm] && $role eq "INPUT" &&
                [[[$iterm getInst] getMaster] getName] eq "ANTENNA_X1" &&
                [[$iterm getMTerm] getName] eq "A"} {
                incr maintenance_loads
                continue
            }
            if {![dict exists $expected $iterm]} {
                lappend problem "unlisted_ITerm:[[$iterm getInst] getName]/[[$iterm getMTerm] getName]"
            }
        }
        if {$found_drivers==1} {lappend sources $net}
        if {$found_drivers==0} {lappend sinks $net}
        if {$found_drivers>1} {lappend problem "multiple_drivers:$name"}
        if {[dict exists $claimed $name]} {lappend problem "claimed_by:[dict get $claimed $name]"}
        foreach term [$net getBTerms] {
            if {![llength [$term getBPins]] && [$term getIoType] eq "OUTPUT" &&
                $group in {U0 U1} && [regexp [format {^%s__outgoing_data\[[0-9]+\]$} $group] [$term getName]]} {
                lappend retained_service_aliases [$term getName]
                continue
            }
            if {[llength [$term getBPins]] || ![string match "${group}__late_*" [$term getName]]} {
                lappend problem "non_fixture_BTerm:[$term getName]"
            }
        }
    }
    if {[llength $sources]!=1 || [llength $sinks]<1} {lappend problem "source_sink_partition"}
    if {[llength $problem]} {
        dict incr tally "$group/requires_review"
        puts $report [join [list $id $group $candidate requires_review [join $problem {;}]] "\t"]
        continue
    }
    if {[llength $retained_service_aliases]} {
        dict incr tally "$group/shared_outgoing_service"
        puts $report [join [list $id $group $candidate shared_outgoing_service $retained_service_aliases] "\t"]
        continue
    }
    if {$maintenance_loads} {dict incr tally "$group/retained_antenna_loads" $maintenance_loads}
    set index 0
    foreach net [concat $sources $sinks] {
        set name [$net getName]
        dict set claimed $name $id
        set terms [$net getITerms]
        set selected {}
        set access parent_escape_required
        foreach iterm $terms {
            set inst [$iterm getInst]
            set mterm [$iterm getMTerm]
            set direction [$mterm getIoType]
            lappend selected [list [$inst getName] [$mterm getName] $direction]
            if {[llength $terms]==1 && [[$inst getMaster] getType] eq "BLOCK"} {
                foreach mpin [$mterm getMPins] {
                    foreach shape [$mpin getGeometry] {
                        if {[[$shape getTechLayer] getRoutingLevel]==10} {set access leaf_m10}
                    }
                }
            }
        }
        set direction [expr {$index==0?"driver":"sink"}]
        puts $identities [join [list $id $index $direction $name $access $selected] "\t"]
        if {$::env(REMOVE_FIXTURE_PORTS) eq "1"} {
            foreach term [$net getBTerms] {odb::dbBTerm_destroy $term}
        }
        incr index
    }
    dict incr tally "$group/exact_existing_cut"
    puts $report [join [list $id $group $candidate exact_existing_cut $index] "\t"]
}
close $identities
close $report
dict for {label count} $tally {puts "FUNCTIONAL_CUTS $label $count"}
if {$::env(REMOVE_FIXTURE_PORTS) eq "1"} {
    write_db $::env(OUTPUT_DB)
}
