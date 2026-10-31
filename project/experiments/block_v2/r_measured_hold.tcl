# Native one-session post-GRT data-delay ECO, based on actual RC081/084/089.
# No clock, RTL state, interface SDC, or timing exception is changed.
set evidence_sha 296decd2c48f6892dcd399a4888f0091ca54149d7d563e55692f54b26e52fc5b
set targets {
 {$auto$ff.cc:337:slice$2874097}
 {$auto$ff.cc:337:slice$2873663}
 {$auto$ff.cc:337:slice$2874223}
 {$auto$ff.cc:337:slice$3749396}
 {$auto$ff.cc:337:slice$2874191}
 {$auto$ff.cc:337:slice$3749652}
 {$auto$ff.cc:337:slice$2871178}
 {$auto$ff.cc:337:slice$2873668}
 {$auto$ff.cc:337:slice$2873669}
 {$auto$ff.cc:337:slice$2794931}
 {$auto$ff.cc:337:slice$2874052}
 {$auto$ff.cc:337:slice$2873851}
 {$auto$ff.cc:337:slice$2794927}
 {$auto$ff.cc:337:slice$2873664}
 {$auto$ff.cc:337:slice$2873506}
 {$auto$ff.cc:337:slice$2873666}
 {$auto$ff.cc:337:slice$2874050}
 {$auto$ff.cc:337:slice$2873665}
 {$auto$ff.cc:337:slice$2874047}
 {$auto$ff.cc:337:slice$2874051}
 {$auto$ff.cc:337:slice$2873538}
 {$auto$ff.cc:337:slice$2874048}
 {$auto$ff.cc:337:slice$2874049}
 {$auto$ff.cc:337:slice$2873535}
 {$auto$ff.cc:337:slice$3749646}
 {$auto$ff.cc:337:slice$2874053}
 {$auto$ff.cc:337:slice$2874214}
 {$auto$ff.cc:337:slice$2809116}
 {$auto$ff.cc:337:slice$2874264}
 {$auto$ff.cc:337:slice$2873524}
}
set target_file [file join [file dirname $::env(DESIGN_CONFIG)] r-hold-targets.json]
if {[lindex [exec sha256sum $target_file] 0] ne $evidence_sha} {error "Measured target evidence changed"}
set block [ord::get_db_block]
if {[$block getName] ne "block_v1_r" || [llength $targets]!=30} {error "Measured R target scope changed"}
set master [[ord::get_db] findMaster BUF_X1]
if {$master eq "NULL"} {error "Missing native data-delay master"}
if {[llength [info commands odb::dbInst_isDoNotTouch]]==1} {
 set getter isDoNotTouch
} elseif {[llength [info commands odb::dbInst_getDoNotTouch]]==1} {
 set getter getDoNotTouch
} else {error "Missing native scoped protection readback"}
proc issue143_preserved_pins {inst} {
 set result {}
 foreach pin [$inst getITerms] {
  set term [$pin getMTerm]
  if {[$term getName] eq "D"} {continue}
  set net [$pin getNet]
  set name [expr {$net eq "NULL" ? "NULL" : [$net getName]}]
  lappend result [list [$term getName] [$term getIoType] $name]
 }
 return [lsort $result]
}
# Check current-session setup at each exact target before adding delay.
set endpoints {}
set number 0
foreach name $targets {
 set inst [$block findInst $name]
 if {$inst eq "NULL" || [[$inst getMaster] getName] ni {DFF_X1 DFF_X2}} {error "Measured R DFF identity changed"}
 set pin [$inst findITerm D]
 if {$pin eq "NULL" || [$pin getNet] eq "NULL"} {error "Measured R data input missing"}
 set sta_pin [get_pins [list ${name}/D]]
 if {[llength $sta_pin]!=1} {error "Measured R STA endpoint missing"}
 set path $::env(RESULTS_DIR)/issue143-measured-setup-$number.rpt
 report_checks -path_delay max -to $sta_pin -group_path_count 1 -digits 9 > $path
 set stream [open $path r];set text [read $stream];close $stream
 if {![regexp {([-+0-9.]+)\s+slack \(MET\)} $text -> slack] || $slack<0.150} {
  error "Measured R endpoint has insufficient current-session setup headroom"
 }
 lappend endpoints [list $inst $pin $slack]
 incr number
}
global_route -start_incremental
set audit [open $::env(RESULTS_DIR)/issue143-measured-hold.tsv w]
puts $audit "scope\ttargets\t30\tbuffers_per_endpoint\t4\tevidence_sha256\t$evidence_sha"
set number 0
foreach row $endpoints {
 lassign $row inst pin slack
 set original [$pin getNet]
 set original_terms {}
 foreach term [$original getITerms] {lappend original_terms "[[$term getInst] getName]/[[$term getMTerm] getName]"}
 set original_ports {};foreach term [$original getBTerms] {lappend original_ports [$term getName]}
 set preserved [issue143_preserved_pins $inst]
 set current $original
 lassign [$inst getLocation] x y
 set core [$block getCoreArea]
 set height [$master getHeight]
 set xbase [expr {max([$core xMin],min($x-8000,[$core xMax]-20000))}]
 set ybase [expr {max([$core yMin],min($y-2*$height,[$core yMax]-2*$height))}]
 puts $audit "endpoint\t$number\t[$inst getName]\t[[$inst getMaster] getName]\t[$original getName]\t$slack"
 for {set i 0} {$i<4} {incr i} {
  set name issue143_r_hold_${number}_$i
  if {[$block findInst $name] ne "NULL" || [$block findNet ${name}_net] ne "NULL"} {error "Duplicate measured R delay"}
  set next [odb::dbNet_create $block ${name}_net]
  set buffer [odb::dbInst_create $block $master $name]
  $buffer setLocation [expr {$xbase+$i*4000}] $ybase
  $buffer setOrient R0;$buffer setPlacementStatus PLACED
  [$buffer findITerm A] connect $current
  [$buffer findITerm Z] connect $next
  foreach term [$buffer getITerms] {
   set kind [[$term getMTerm] getSigType]
   if {$kind in {POWER GROUND}} {
    set pg [$block findNet [expr {$kind eq "POWER" ? "VDD" : "VSS"}]]
    if {$pg eq "NULL"} {error "Original R PG missing"}
    $term connect $pg
   }
  }
  set_dont_touch [get_cells $name]
  if {![$buffer $getter]} {error "Measured R delay protection not retained"}
  puts $audit "buffer\t$number\t$i\t$name\tBUF_X1\t[$current getName]\t[$next getName]"
  set current $next
 }
 set protected [$inst $getter]
 $inst setDoNotTouch false
 try {$pin disconnect;$pin connect $current} finally {$inst setDoNotTouch $protected}
 if {[$inst $getter]!=$protected || [issue143_preserved_pins $inst] ne $preserved} {error "R CK/Q/PG or existing protection changed"}
 if {[$pin getNet] ne $current || [llength [$current getITerms]]!=2 || [llength [$current getBTerms]]!=0} {error "Measured R delay endpoint disconnected"}
 set now_terms {};foreach term [$original getITerms] {lappend now_terms "[[$term getInst] getName]/[[$term getMTerm] getName]"}
 set expected_terms [lsearch -all -inline -not -exact $original_terms "[$inst getName]/D"]
 lappend expected_terms issue143_r_hold_${number}_0/A
 set now_ports {};foreach term [$original getBTerms] {lappend now_ports [$term getName]}
 if {[lsort $now_terms] ne [lsort $expected_terms] || [lsort $now_ports] ne [lsort $original_ports]} {error "Non-target R fanout changed"}
 puts $audit "verified\t$number\tCK_Q_PG_preserved\tother_fanout_preserved\tprotection_restored"
 incr number
}
close $audit
global_connect
detailed_placement_helper
check_placement -verbose
global_route -end_incremental
estimate_parasitics -global_routing
set_propagated_clock [all_clocks]
sta::find_timing
set counts [list [sta::max_capacitance_violation_count] [sta::max_slew_violation_count] [sta::endpoint_violation_count max] [sta::endpoint_violation_count min]]
set stream [open $::env(RESULTS_DIR)/issue143-measured-hold-checks.tsv w]
puts $stream [join $counts "\t"];close $stream
report_checks -path_delay min_max -group_path_count 3 -digits 9 > $::env(RESULTS_DIR)/issue143-measured-hold-timing.rpt
if {$counts ne {0 0 0 0}} {error "Measured R data delays did not close current native GRT checks"}
write_guides $::env(RESULTS_DIR)/route.guide
