# Write only a linked Verilog view, leaving the reference ODB/GDS intact.
read_db $::env(CFJ_FINAL_ODB)
set block [ord::get_db_block]
set run $::env(CFJ_OVERLAY_DIR)
set stream [open $run/stitched-ports.tsv r]
while {[gets $stream line] >= 0} {
    lassign [split $line "\t"] source sink
    set outgoing [$block findBTerm $source]
    set incoming [$block findBTerm $sink]
    set outnet [$outgoing getNet]
    set innet [$incoming getNet]
    if {$outnet eq $innet || [llength [$outnet getBTerms]] != 1 ||
        [llength [$innet getBTerms]] != 1} {error "aliased cut pair $source $sink"}
    foreach iterm [$innet getITerms] {
        set inst [$iterm getInst]
        set protected [$inst isDoNotTouch]
        if {$protected} {$inst setDoNotTouch 0}
        try {
            $iterm disconnect
            $iterm connect $outnet
        } finally {
            if {$protected} {$inst setDoNotTouch 1}
        }
    }
    odb::dbBTerm_destroy $incoming
    odb::dbBTerm_destroy $outgoing
}
close $stream
write_verilog $run/stitched.v
