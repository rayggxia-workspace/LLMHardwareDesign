set root /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu
read_db $root/runs/C-v20-native-clock4/global-candidate.odb
source $root/c-global-electrical-specs.tcl
set b [ord::get_db_block]
proc norm {s} {return [string map [list "\\" ""] $s]}
set im {};set bm {}
foreach i [$b getInsts] {dict set im [norm [$i getName]] $i}
foreach bt [$b getBTerms] {dict set bm [norm [$bt getName]] $bt}
set f [open $root/c-global-electrical-classification.tsv w]
puts $f "kind\tpin\tlocation_kind\tnet\tsigtype\tdriver\tdriver_master\tdriver_class\tmacro_sinks\tports"
set summary {}
foreach spec $specs {
 lassign $spec kind name
 set name [norm $name]
 set slash [string last / $name]
 if {$slash<0} {
  if {![dict exists $bm $name]} {error "Missing exact port $name"}
  set bt [dict get $bm $name];set net [$bt getNet];set location port
 } else {
  set in [string range $name 0 [expr {$slash-1}]]
  set mt [string range $name [expr {$slash+1}] end]
  if {![dict exists $im $in]} {error "Missing exact instance $in"}
  set i [dict get $im $in];set it [$i findITerm $mt]
  if {$it eq "NULL"} {
   foreach test [$i getITerms] {if {[norm [[$test getMTerm] getName]] eq $mt} {set it $test;break}}
  }
  if {$it eq "NULL"} {error "Missing exact pin $name"}
  set net [$it getNet]
  set location [expr {[[$i getMaster] isBlock] ? "macro_pin" : "standard_pin"}]
 }
 set drivers {};set macros {};set ports {}
 foreach it [$net getITerms] {
  set i [$it getInst];set m [$i getMaster]
  if {[[$it getMTerm] getIoType] eq "OUTPUT"} {lappend drivers $i}
  if {[$m isBlock] && [[$it getMTerm] getIoType] eq "INPUT"} {lappend macros "[$i getName]/[[$it getMTerm] getName]"}
 }
 foreach bt [$net getBTerms] {lappend ports "[$bt getName]:[$bt getIoType]"}
 set dn {};set dm {};set class external_input
 if {[llength $drivers]==1} {
  set di [lindex $drivers 0];set dn [$di getName];set dm [[$di getMaster] getName]
  if {[$net getSigType] eq "CLOCK"} {set class clock} elseif {[[$di getMaster] isBlock]} {set class macro_driver} elseif {[string match hold* $dn] || [string match i289_donly* $dn]} {set class hold_buffer} elseif {[regexp {^(BUF|CLKBUF|INV)_X} $dm]} {set class other_buffer} else {set class other_logic}
 } elseif {[llength $drivers]>1} {set class multiple_drivers}
 dict incr summary [list $kind $class]
 puts $f [join [list $kind $name $location [$net getName] [$net getSigType] $dn $dm $class [join $macros ,] [join $ports ,]] "\t"]
}
close $f
puts $summary