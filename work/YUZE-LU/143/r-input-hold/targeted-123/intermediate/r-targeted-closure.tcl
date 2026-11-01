# Native one-session post-GRT data-delay ECO, based on actual RC100/104/106.
# No clock, RTL state, interface SDC, or timing exception is changed.
set folder [file dirname $::env(DESIGN_CONFIG)]
source [file join $folder r-targeted-config.tcl]
set target_file [file join $folder r-targeted-evidence.json]
if {[lindex [exec sha256sum $target_file] 0] ne $evidence_sha} {error "Targeted actual-RC evidence changed"}
set block [ord::get_db_block]
if {[$block getName] ne "block_v1_r" || [llength $targets]<1 || [llength $targets]>512 || [llength $resize_targets]!=10} {error "Measured R target scope changed"}
# Preserve the actual optimized/rerouted checkpoint even if admission rejects
# below. This is a recovery checkpoint, never a completed route or final leaf.
write_db $::env(RESULTS_DIR)/issue143-targeted-pre.odb
write_sdc -no_timestamp $::env(RESULTS_DIR)/issue143-targeted-pre.sdc
write_guides $::env(RESULTS_DIR)/issue143-targeted-pre.guide
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
 set path $::env(RESULTS_DIR)/issue143-targeted-setup-$number.rpt
 report_checks -path_delay max -to $sta_pin -group_path_count 1 -digits 9 > $path
 set stream [open $path r];set text [read $stream];close $stream
 if {![regexp {([-+0-9.]+)\s+slack \(MET\)} $text -> slack] || $slack<0.100} {
  error "Measured R endpoint has insufficient current-session setup headroom"
 }
 lappend endpoints [list $inst $pin $slack]
 incr number
}
# GRT estimates can retain electrical violations that detailed routing closes.
# Snapshot the native baseline before the ECO; final actual-RC gates remain0.
sta::find_timing
set stream [open $::env(RESULTS_DIR)/issue143-targeted-before-checks.tsv w]
puts $stream [join [list [sta::max_capacitance_violation_count] [sta::max_slew_violation_count] [sta::endpoint_violation_count max] [sta::endpoint_violation_count min]] "\t"]
close $stream
report_check_types -max_capacitance -max_slew -violators -digits 12 -no_line_splits > $::env(RESULTS_DIR)/issue143-targeted-before-electrical.rpt
global_route -start_incremental
set audit [open $::env(RESULTS_DIR)/issue143-targeted-hold.tsv w]
puts $audit "scope\ttargets\t[llength $targets]\tbuffers_per_endpoint\t4\tevidence_sha256\t$evidence_sha"
#116 introduced one capacitance/slew violation on this exact MUX output.
#119 read its original two-load signal net and master from immutable pre-ECO DB.
#Strengthen only this equivalent combinational cell; all pins/placement and
#protection must survive. Current-session hold guard and final gates still apply.
set electrical_name {$abc$4429625$auto$blifparse.cc:397:parse_blif$4540226}
set electrical_inst [$block findInst $electrical_name]
if {$electrical_inst eq "NULL" || [[$electrical_inst getMaster] getName] ne "MUX2_X1" || [$electrical_inst $getter]} {error "Measured electrical MUX identity/protection changed"}
set electrical_pins [issue143_preserved_pins $electrical_inst]
set electrical_location [$electrical_inst getLocation]
set electrical_net [[$electrical_inst findITerm Z] getNet]
if {[$electrical_net getSigType] ne "SIGNAL" || [llength [$electrical_net getBTerms]]!=0 || [llength [$electrical_net getITerms]]!=3} {error "Measured electrical MUX fanout changed"}
report_checks -path_delay min -through [get_pins [list $electrical_name/Z]] -group_path_count 1 -digits 9 > $::env(RESULTS_DIR)/issue143-targeted-electrical-mux-min.rpt
set stream [open $::env(RESULTS_DIR)/issue143-targeted-electrical-mux-min.rpt r];set text [read $stream];close $stream
if {![regexp {([-+0-9.]+)\s+slack \(MET\)} $text -> electrical_slack] || $electrical_slack<0.100} {error "Measured electrical MUX has insufficient hold headroom"}
if {[replace_cell [get_cells [list $electrical_name]] MUX2_X2]!=1} {error "Pinned native replace_cell rejected equivalent MUX2_X2"}
if {[[$electrical_inst getMaster] getName] ne "MUX2_X2" || [$electrical_inst $getter] || [$electrical_inst getLocation] ne $electrical_location || [issue143_preserved_pins $electrical_inst] ne $electrical_pins} {error "Electrical MUX resize changed other properties"}
puts $audit "electrical_resize\t$electrical_name\tMUX2_X1\tMUX2_X2\t$electrical_slack\tconnections_location_protection_preserved"
# Resize only signal repeaters verified in the actual final-RC topology.
# Preserve their input/output/PG connectivity, position and protection state.
foreach row $resize_targets {
 lassign $row name old_master
 set inst [$block findInst $name]
 if {$inst eq "NULL" || [[$inst getMaster] getName] ne $old_master || [$inst $getter]} {error "Measured repeater identity/protection changed"}
 set before_pins [issue143_preserved_pins $inst]
 set before_location [$inst getLocation]
 foreach label {A Z} {
  set pin [$inst findITerm $label]
  set net [$pin getNet]
  if {$net eq "NULL" || [$net getSigType] ne "SIGNAL" || [llength [$net getBTerms]]!=0 || [llength [$net getITerms]]!=2} {error "Measured repeater fanout/signal scope changed"}
 }
 report_checks -path_delay min -through [get_pins [list $name/A]] -group_path_count 1 -digits 9 > $::env(RESULTS_DIR)/issue143-targeted-repeater-$name.rpt
 set stream [open $::env(RESULTS_DIR)/issue143-targeted-repeater-$name.rpt r];set text [read $stream];close $stream
 if {![regexp {([-+0-9.]+)\s+slack \(MET\)} $text -> slack] || $slack<0.300} {error "Measured repeater has insufficient current-session hold headroom"}
 if {[replace_cell [get_cells [list $name]] BUF_X4]!=1} {error "Pinned native replace_cell rejected equivalent BUF_X4"}
 if {[[$inst getMaster] getName] ne "BUF_X4" || [$inst $getter] || [$inst getLocation] ne $before_location || [issue143_preserved_pins $inst] ne $before_pins} {error "Targeted repeater resize changed other properties"}
 puts $audit "resize\t$name\t$old_master\tBUF_X4\t$slack\tconnections_location_protection_preserved"
}
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
  set name issue143_r_closure_${number}_$i
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
 lappend expected_terms issue143_r_closure_${number}_0/A
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
set stream [open $::env(RESULTS_DIR)/issue143-targeted-hold-checks.tsv w]
puts $stream [join $counts "\t"];close $stream
report_checks -path_delay min_max -group_path_count 3 -digits 9 > $::env(RESULTS_DIR)/issue143-targeted-hold-timing.rpt
report_check_types -max_capacitance -max_slew -violators -digits 12 -no_line_splits > $::env(RESULTS_DIR)/issue143-targeted-after-electrical.rpt
exec python3 [file join [file dirname $::env(DESIGN_CONFIG)] r-electrical-stage.py] \
 --before $::env(RESULTS_DIR)/issue143-targeted-before-electrical.rpt \
 --after $::env(RESULTS_DIR)/issue143-targeted-after-electrical.rpt \
 --before-counts $::env(RESULTS_DIR)/issue143-targeted-before-checks.tsv \
 --after-counts $::env(RESULTS_DIR)/issue143-targeted-hold-checks.tsv \
 --out $::env(RESULTS_DIR)/issue143-targeted-electrical-stage.json
write_guides $::env(RESULTS_DIR)/route.guide
