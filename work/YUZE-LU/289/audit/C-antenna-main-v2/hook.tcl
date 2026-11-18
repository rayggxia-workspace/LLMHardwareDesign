# Pure OpenDB trial edit. Load the exact candidate ODB first; no route or legalization here.
# All ports, nets, anchors and names are validated before the first mutation.
set pkg [file dirname [file normalize [info script]]]
source $pkg/plan.tcl
source $pkg/geometry-all.tcl
set block [ord::get_db_block]
if {[$block getName] ne "cfj_group_c_memory_legacy"} {error "Not a C parent candidate"}
set master [[ord::get_db] findMaster ANTENNA_X1]
if {$master eq "NULL"} {error "Verified ANTENNA_X1 missing"}
if {[$master getWidth]!=380 || [$master getHeight]!=2800} {error "ANTENNA_X1 geometry differs from qualified Nangate cell"}
foreach pin {A VDD VSS} {if {[$master findMTerm $pin] eq "NULL"} {error "Diode pin missing $pin"}}
if {[[$master findMTerm A] getIoType] ne "INPUT"} {error "Unexpected diode A direction"}
foreach rail {VDD VSS} {if {[$block findNet $rail] eq "NULL"} {error "Power rail missing $rail"}}
set core [$block getCoreArea]
proc c_ant_output_snapshot {block pkg} {
 set f [open $pkg/selected-outputs.txt];set rows {};set seen [dict create]
 while {[gets $f port]>=0} {
  set port [string trim $port];if {$port eq ""} {continue}
  if {[dict exists $seen $port]} {error "Repeated selected port"};dict set seen $port 1
  set bt [$block findBTerm $port]
  if {$bt eq "NULL" || [$bt getIoType] ne "OUTPUT"} {error "Selected OUTPUT missing $port"}
  set net [$bt getNet];set drivers {}
  foreach it [$net getITerms] {if {[[$it getMTerm] getIoType] eq "OUTPUT"} {lappend drivers $it}}
  if {[llength $drivers]!=1} {error "Selected driver cardinality $port"}
  set it [lindex $drivers 0];set inst [$it getInst]
  if {[[$inst getMaster] getName] ne "BUF_X8"} {error "Selected driver not BUF_X8 $port"}
  lappend rows [join [list $port [$net getName] [$inst getName] [[$inst getMaster] getName] [[$it getMTerm] getName]] "\t"]
 }
 close $f;if {[llength $rows]!=153} {error "Expected153 selected outputs"};return [lsort $rows]
}
set outputs_before [c_ant_output_snapshot $block $pkg]
set geometry_before [geometry_snapshot antenna-interface-before.tsv]
set old_inst_count [llength [$block getInsts]]
set old_net_count [llength [$block getNets]]
set selections {};set seen_nets [dict create]
foreach spec $c_ant_plan {
 lassign $spec netname ports newname
 set net [$block findNet $netname]
 if {$net eq "NULL" || [dict exists $seen_nets $netname]} {error "Missing/repeated expected net $netname"}
 dict set seen_nets $netname 1
 if {[$block findInst $newname] ne "NULL"} {error "Hook already applied/name collision $newname"}
 set centers {}
 foreach port $ports {
  set bt [$block findBTerm $port]
  if {$bt eq "NULL" || [$bt getIoType] ne "INPUT" || [$bt getNet] ne $net} {error "Expected INPUTport-to-net changed: $port -> $netname"}
  foreach bp [$bt getBPins] {foreach box [$bp getBoxes] {lappend centers [list [expr {([$box xMin]+[$box xMax])/2}] [expr {([$box yMin]+[$box yMax])/2}]]}}
 }
 if {![llength $centers]} {error "No current BPin geometry $netname"}
 set candidates {}
 foreach it [$net getITerms] {
  set inst [$it getInst];set im [$inst getMaster];set imname [$im getName]
  if {$imname eq "ANTENNA_X1"} {error "Existing parent diode requires separate review $netname"}
  if {[[$it getMTerm] getIoType] ne "INPUT" || [$im isBlock] || ![regexp {_X[0-9]+$} $imname]} {continue}
  if {[$inst getPlacementStatus] ni {PLACED FIRM LOCKED}} {continue}
  set pinpoints {}
  foreach g [$it getGeometries] {lassign $g layer rect;lappend pinpoints [list [expr {([$rect xMin]+[$rect xMax])/2}] [expr {([$rect yMin]+[$rect yMax])/2}]]}
  set mode exact_current_input_pin
  if {![llength $pinpoints]} {set pinpoints [list [$inst getLocation]];set mode fallback_current_inst_origin_no_pin_geometry}
  set best 9223372036854975807
  foreach q $pinpoints {lassign $q px py;foreach p $centers {lassign $p bx by;set dist [expr {abs($px-$bx)+abs($py-$by)}];if {$dist<$best} {set best $dist}}}
  lappend candidates [list $best [$inst getName] [[$it getMTerm] getName] $inst $it $mode]
 }
 if {![llength $candidates]} {error "No placed receiving standard-cell INPUT pin on $netname; no implicit fallback"}
 # Deterministic tie-break by current instance and pin names, then actual pin-to-BPin distance.
 set candidates [lsort -dictionary -index 2 $candidates]
 set candidates [lsort -dictionary -index 1 $candidates]
 set choice [lindex [lsort -integer -index 0 $candidates] 0]
 lassign $choice distance instname pinname anchor terminal mode
 lassign [$anchor getLocation] ax ay
 set x [expr {$ax+[[$anchor getMaster] getWidth]}];set y $ay;set side right
 if {$x+[$master getWidth]>[$core xMax]} {set x [expr {$ax-[$master getWidth]}];set side fallback_left_core_edge}
 if {$x<[$core xMin] || $x+[$master getWidth]>[$core xMax] || $y<[$core yMin] || $y+[$master getHeight]>[$core yMax]} {error "No legal core-adjacent initial location $netname"}
 lappend selections [list $netname $ports $newname $net $anchor $terminal $instname $pinname $distance $mode $side $x $y [$anchor getOrient] $ax $ay]
}
if {[llength $selections]!=549} {error "Expected549 source-bound input networks"}
set f [open antenna-insertions.tsv w]
puts $f "net\tports\tdiode\tanchor\tpin\tanchor_master\tanchor_x\tanchor_y\tdistance_dbu\tanchor_mode\tplacement_mode\tdiode_x\tdiode_y\torient"
foreach chosen $selections {
 lassign $chosen netname ports newname net anchor terminal instname pinname distance mode side x y orient ax ay
 set diode [odb::dbInst_create $block $master $newname]
 $diode setOrient $orient;$diode setLocation $x $y;$diode setPlacementStatus PLACED
 [$diode findITerm A] connect $net
 foreach rail {VDD VSS} {[$diode findITerm $rail] connect [$block findNet $rail]}
 puts $f [join [list $netname [join $ports ,] $newname $instname $pinname [[$anchor getMaster] getName] $ax $ay $distance $mode $side $x $y $orient] "\t"]
}
close $f
if {[llength [$block getInsts]]!=$old_inst_count+549 || [llength [$block getNets]]!=$old_net_count} {error "Unexpected object count change"}
foreach chosen $selections {
 lassign $chosen netname ports newname net
 set diode [$block findInst $newname]
 if {[[$diode findITerm A] getNet] ne $net} {error "Diode A binding mismatch"}
 foreach rail {VDD VSS} {if {[[$diode findITerm $rail] getNet] ne [$block findNet $rail]} {error "Diode PG logical binding mismatch"}}
 set count 0;foreach it [$net getITerms] {if {[[[$it getInst] getMaster] getName] eq "ANTENNA_X1"} {incr count}}
 if {$count!=1} {error "Expectedone actual ANTENNA_X1 on $netname"}
}
if {[c_ant_output_snapshot $block $pkg] ne $outputs_before} {error "153 selected driver bindings changed"}
if {[geometry_snapshot antenna-interface-after.tsv] ne $geometry_before} {error "Interface/die/macro geometry changed"}
set f [open selected-drivers.tsv w];puts $f [join $outputs_before "\n"];close $f
puts C_ANTENNA_TRIAL_549_STRUCTURAL_CHECKS_PASS_PENDING_LEGALIZATION_ROUTING_AND_FULL_SIGNOFF
