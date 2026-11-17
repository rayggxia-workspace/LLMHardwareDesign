from pathlib import Path
p=Path(__file__).parent
s=(p/'u-electrical-edit-v2.tcl').read_text()
s=s.replace('set source $root/runs/U-v11-targeted-n4-x8/flow/results/nangate45/u-overlay-current/base','set source $::env(U_SOURCE)')
a=s.index('foreach name {wire40495');b=s.index('proc safe_location',a)
s=s[:a]+'''foreach name {place17297 place17567} {
 set i [$block findInst $name]
 if {$i eq "NULL" || [[$i getMaster] getName] ne "BUF_X1"} {error "Diagnosed cap driver mismatch $name"}
 $i swapMaster [[ord::get_db] findMaster BUF_X4]
 puts $f "$name\\tBUF_X1\\tBUF_X4"
}
'''+s[b:]
a=s.index('set bt [$block findBTerm');b=s.index('foreach spec ',a)
s=s[:a]+s[b:]
a=s.index('foreach spec ');b=s.index(' {\n lassign $spec',a)
s=s[:a]+'''foreach spec {{datapath.n32 {s_rsp_data[46]} datapath.store n32_46} {datapath.store {req_data[114]} wire22300 store114} {datapath.store {req_data[116]} wire40491 store116} {datapath.store {req_data[118]} wire22297 store118} {datapath.store {req_data[124]} wire22294 store124} {datapath.store req_write wire22499 storewrite} {elementwise {in_data[101]} {legacy_e.e_in_data[101]$_SDFFCE_PN0P_} e101}}'''+s[b:]
s=s.replace('set dp [[$block findInst $driver] getBBox]', '''set matches {}
 foreach candidate [$block getInsts] {
  if {[string map [list "\\\\" ""] [$candidate getName]] eq $driver} {lappend matches $candidate}
 }
 if {[llength $matches]!=1} {error "Driver lookup $driver"}
 set di [lindex $matches 0]
 set dp [$di getBBox]
 if {[[$di getMaster] isBlock]} {
  set out [$di findITerm {rsp_data[46]}]
  set geometries [$out getGeometries]
  if {[llength $geometries]<1} {error "Macro driver lacks actual geometry"}
  set dp [lindex [lindex $geometries end] 1]
 }''')
s=s.replace('close $f\nwrite_db', '''set matches {}
foreach i [$block getInsts] {
 if {[string map [list "\\\\" ""] [$i getName]] eq {controller.task_packet[89]$_DFFE_PP_}} {lappend matches $i}
}
if {[llength $matches]!=1} {error "Exact task_packet89 state lookup"}
set si [lindex $matches 0]
set sink [$si findITerm D]
set prev [$sink getNet]
$sink disconnect
lassign [$si getLocation] x y
for {set j 0} {$j<$::env(U_TARGET_HOLD_COUNT)} {incr j} {
 set name i289_guardant_hold89_$j
 set i [odb::dbInst_create $block [[ord::get_db] findMaster CLKBUF_X1] $name]
 $i setLocation $x $y
 $i setPlacementStatus PLACED
 set net [odb::dbNet_create $block ${name}_net]
 [$i findITerm A] connect $prev
 [$i findITerm Z] connect $net
 set prev $net
}
$sink connect $prev
close $f
write_db''')
(p/'u-guardant-edit-v1.tcl').write_text(s,newline='\n')