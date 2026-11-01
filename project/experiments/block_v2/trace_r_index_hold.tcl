# Read-only diagnostic of all hold failures on one immutable actual-RC design.
set_thread_count 16
set platform /OpenROAD-flow-scripts/flow/platforms/nangate45
read_liberty $platform/lib/NangateOpenCellLibrary_typical.lib
read_db $::env(BV1_ODB)
read_sdc $::env(BV1_SDC)
read_spef $::env(BV1_SPEF)
set_propagated_clock [all_clocks]
sta::find_timing
report_checks -path_delay max -slack_max 0 -group_path_count 10000 -endpoint_path_count 1 -digits 9 -format full_clock_expanded > all-setup.rpt
set f [open all-setup.rpt r];set setup_content [read $f];close $f
set setup_endpoints [dict create]
foreach {line endpoint} [regexp -all -inline -line {^Endpoint: (\S+)} $setup_content] {
 if {[dict exists $setup_endpoints $endpoint]} {error "Duplicate reported setup endpoint"}
 dict set setup_endpoints $endpoint 1
}
if {[dict size $setup_endpoints] != [sta::endpoint_violation_count max]} {error "Setup report omitted failing endpoints"}
# Record actual buffer connectivity on the failing setup paths before proposing
# a physical ECO. This is read-only, including for any clock or protected cells.
set block [ord::get_db_block]
set seen [dict create]
set f [open setup-buffer-topology.tsv w]
puts $f "instance\tmaster\tprotected\tpin\tnet\tsignal_type\tx\ty\tconnected_iterms\tconnected_ports"
foreach line [split $setup_content \n] {
 if {![regexp { ([^[:space:]]+)/[^[:space:]]+ \((BUF_[^)]+)\)$} $line ignored name master]} {continue}
 if {[dict exists $seen $name]} {continue}
 dict set seen $name 1
 set inst [$block findInst $name]
 if {$inst eq "NULL" || [[$inst getMaster] getName] ne $master} {error "Setup buffer identity mismatch"}
 if {[llength [info commands odb::dbInst_isDoNotTouch]]==1} {set protected [$inst isDoNotTouch]} else {set protected [$inst getDoNotTouch]}
 lassign [$inst getLocation] x y
 foreach pin [$inst getITerms] {
  if {[[$pin getMTerm] getSigType] in {POWER GROUND}} {continue}
  set net [$pin getNet];if {$net eq "NULL"} {continue}
  set terms {};foreach term [$net getITerms] {lappend terms "[[$term getInst] getName]/[[$term getMTerm] getName]"}
  set ports {};foreach term [$net getBTerms] {lappend ports [$term getName]}
  puts $f [join [list $name $master $protected [[$pin getMTerm] getName] [$net getName] [$net getSigType] $x $y [lsort $terms] [lsort $ports]] "\t"]
 }
}
close $f
# Include small-positive reset paths so a local delay ECO is based on measured
# headroom, rather than repeatedly exposing the next almost-failing endpoint.
report_checks -path_delay min -from [get_ports {cmd_index*}] -slack_max 0.050 -group_path_count 10000 -endpoint_path_count 1 -digits 9 -format full_clock_expanded > index-near.rpt
set f [open index-near.rpt r];set reset_content [read $f];close $f
# These are actual long-wire repeaters identified by105, not redundant delay.
# Read both max and min through each before considering stronger drive.
foreach name {place571072} {
 set pin [get_pins [list ${name}/A]]
 if {[llength $pin]!=1} {error "Measured shared buffer not found"}
 report_checks -path_delay min_max -through $pin -group_path_count 10 -endpoint_path_count 1 -digits 9 -format full_clock_expanded > shared-buffer.rpt
}
set names [list place571072 {$abc$4429625$auto$blifparse.cc:397:parse_blif$4767593} {$auto$ff.cc:337:slice$2870365} {$auto$ff.cc:337:slice$2870892}]
set f [open target-topology.tsv w]
puts $f "instance\tmaster\tprotected\tstatus\torient\tx\ty\tpin\tnet\ttype\tterms\tports"
foreach name $names {
 set inst [$block findInst $name]
 if {$inst eq "NULL"} {error "Target instance missing: $name"}
 if {[llength [info commands odb::dbInst_isDoNotTouch]]==1} {set protected [$inst isDoNotTouch]} else {set protected [$inst getDoNotTouch]}
 lassign [$inst getLocation] x y
 foreach pin [$inst getITerms] {
  set net [$pin getNet];if {$net eq "NULL"} {continue}
  if {[[$pin getMTerm] getSigType] in {POWER GROUND}} {continue}
  set terms {};foreach t [$net getITerms] {lappend terms "[[$t getInst] getName]/[[$t getMTerm] getName]"}
  set ports {};foreach t [$net getBTerms] {lappend ports [$t getName]}
  puts $f [join [list $name [[$inst getMaster] getName] $protected [$inst getPlacementStatus] [$inst getOrient] $x $y [[$pin getMTerm] getName] [$net getName] [$net getSigType] [lsort $terms] [lsort $ports]] "\t"]
 }
}
close $f
set f [open buffer-master-pins.tsv w]
puts $f "master\twidth\theight\tpin\tdirection\tlayer\txmin\tymin\txmax\tymax"
set wanted {BUF_X1 BUF_X2 BUF_X4 BUF_X8 BUF_X16 BUF_X32 CLKBUF_X1 CLKBUF_X2 CLKBUF_X3}
foreach library [[ord::get_db] getLibs] {
 foreach master [$library getMasters] {
  set name [$master getName];if {$name ni $wanted} {continue}
  foreach term [$master getMTerms] {
   if {[$term getSigType] in {POWER GROUND}} {continue}
   foreach pin [$term getMPins] {foreach box [$pin getGeometry] {
    if {[$box isVia]} {error "Unexpected master pin via"}
    puts $f [join [list $name [$master getWidth] [$master getHeight] [$term getName] [$term getIoType] [[$box getTechLayer] getName] [$box xMin] [$box yMin] [$box xMax] [$box yMax]] "\t"]
   }}
  }
 }
}
close $f

report_checks -path_delay min -slack_max 0 -group_path_count 10000 -endpoint_path_count 1 -digits 9 -format full_clock_expanded > all-hold.rpt
set stream [open all-hold.rpt r]
set content [read $stream]
close $stream
set endpoints [dict create]
foreach {line endpoint} [regexp -all -inline -line {^Endpoint: (\S+)} $content] {
 if {[dict exists $endpoints $endpoint]} {error "Duplicate reported hold endpoint"}
 dict set endpoints $endpoint 1
}
if {[dict size $endpoints] != [sta::endpoint_violation_count min]} {error "Hold report omitted failing endpoints"}
foreach {line endpoint} [regexp -all -inline -line {^Endpoint: (\S+)} $reset_content] {dict set endpoints $endpoint 1}
set block [ord::get_db_block]
set stream [open endpoint-index.tsv w]
puts $stream "index\tendpoint\tmaster\tdata_net"
set number 0
dict for {endpoint ignored} $endpoints {
 set inst [$block findInst $endpoint]
 if {$inst eq "NULL" || $inst eq ""} {error "Hold endpoint not found in actual ODB"}
 set term [$inst findITerm D]
 if {$term eq "NULL" || $term eq "" || [[$term getMTerm] getIoType] ne "INPUT"} {error "Hold endpoint data pin missing"}
 set pin [get_pins [list ${endpoint}/D]]
 if {[llength $pin] != 1} {error "Hold endpoint STA pin missing"}
 puts $stream "$number\t$endpoint\t[[$inst getMaster] getName]\t[[$term getNet] getName]"
 report_checks -path_delay max -to $pin -group_path_count 1 -digits 9 -format full_clock_expanded > endpoint-setup-$number.rpt
 incr number
}
close $stream
set f [open summary.tsv w]
puts $f "diagnostic_only\ttrue"
puts $f "native_leaf_accepted\tfalse"
puts $f "setup_checks\t[sta::endpoint_violation_count max]"
puts $f "hold_checks\t[sta::endpoint_violation_count min]"
close $f
report_worst_slack -max -digits 9 > timing.rpt
report_worst_slack -min -digits 9 >> timing.rpt
