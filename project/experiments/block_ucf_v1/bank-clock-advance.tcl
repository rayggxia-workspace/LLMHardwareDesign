# Advance the measured SRAM-only CTS branch without changing clock semantics.
if {$ucf_bank_clock_stages ni {2 3}} {error "Unexpected SRAM CTS experiment"}
set start [expr {18 - $ucf_bank_clock_stages}]
set sink [[$block findInst clkbuf_0_clk] findITerm A]
set rewired [$block findNet delaynet_17_core]
if {[$sink getNet] ne $rewired || [llength [$rewired getBTerms]] != 0 ||
    [llength [$rewired getITerms]] != 2} {error "SRAM clock branch terminal changed"}
set upstream [$block findNet delaynet_[expr {$start - 1}]_core]
if {$upstream eq "NULL" || [llength [$upstream getITerms]] != 2 ||
    [llength [$upstream getBTerms]] != 0} {error "Unexpected loads on the retained delay stage"}
set removal {}
for {set i $start} {$i < 18} {incr i} {
    set inst [$block findInst delaybuf_${i}_core]
    set input [$block findNet delaynet_[expr {$i - 1}]_core]
    set output [$block findNet delaynet_${i}_core]
    if {$inst eq "NULL" || [[$inst getMaster] getName] ni {CLKBUF_X1 CLKBUF_X3} ||
        [[$inst findITerm A] getNet] ne $input || [[$inst findITerm Z] getNet] ne $output ||
        [llength [$output getITerms]] != 2 || [llength [$output getBTerms]] != 0} {
        error "Measured SRAM clock series topology differs at stage $i"
    }
    lappend removal [list $inst $output]
}
foreach entry $removal {
    lassign $entry cell net
    $cell setDoNotTouch false
    $net setDoNotTouch false
}
$upstream setDoNotTouch false
set sink_cell [$sink getInst]
set original_protection [$sink_cell $getter]
$sink_cell setDoNotTouch false
$sink disconnect
foreach entry $removal {
    lassign $entry cell net
    odb::dbInst_destroy $cell
}
$sink connect $upstream
$sink_cell setDoNotTouch $original_protection
foreach entry $removal {
    lassign $entry cell net
    if {[llength [$net getITerms]] != 0 || [llength [$net getBTerms]] != 0} {error "Removed stage still has load"}
    odb::dbNet_destroy $net
}
if {[$sink getNet] ne $upstream || [llength [$upstream getITerms]] != 2} {
    error "SRAM clock branch disconnected"
}
puts "UCF_MEASURED_BANK_CLOCK advanced existing four-bank branch by $ucf_bank_clock_stages noninverting stages"
