set_thread_count $::env(SLURM_CPUS_PER_TASK)
read_db $::env(NATIVE_P_DB)
set block [ord::get_db_block]
set fin [open $::env(NATIVE_P_PORTS) r]
set fout [open $::env(NATIVE_P_REPORT) w]
puts $fout "logical_pin\tnet\tio\tbt_count\thas_wire\tall_nets_terminals"
while {[gets $fin row] >= 0} {
    lassign [split $row "\t"] family name direction
    if {$family eq "p_dma_desc"} {continue}
    set term [$block findBTerm $name]
    if {$term eq "NULL" || [$term getIoType] ne $direction} {
        error "wrong group interface $name"
    }
    set net [$term getNet]
    set iterms {}
    foreach sink [$net getITerms] {
        set inst [$sink getInst]
        set cell [$inst getMaster]
        set pin [$sink getMTerm]
        lappend iterms [list [$inst getName] [$cell getType] [$pin getName] [$pin getIoType]]
    }
    puts $fout [join [list $name [$net getName] $direction [llength [$net getBTerms]] [expr {[$net getWire] ne "NULL"}] $iterms] "\t"]
}
close $fin
close $fout
