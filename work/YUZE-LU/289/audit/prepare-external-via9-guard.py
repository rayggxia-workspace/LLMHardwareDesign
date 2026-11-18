from pathlib import Path
r=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117');p=r/'audit/C-v27-external-via9-guard';p.mkdir(exist_ok=False)
rows=[s for s in (r/'audit/C-v27-physical/rcx-material-120031/bpins.tsv').read_text().splitlines() if s.split('\t')[0] in ['event_packet_o[65]','mem_rd_rsp_data[125]','cfg_req_address_i[5]','cfg_req_total_bytes_i[2]']];assert len(rows)==4;(p/'expected-bpins.tsv').write_text('\n'.join(rows)+'\n')
(p/'hook.tcl').write_text('''# Virtual via9 routing keepouts only. No physical metal or BPin edit.
namespace eval ::c_external_via9_guard {
set package [file dirname [file normalize [info script]]]
set block [::ord::get_db_block]
set tech [[::ord::get_db] getTech]
if {[$tech getDbUnitsPerMicron]!=2000} {error "Unexpected DBU"}
set layer [$tech findLayer via9]
if {$layer eq "NULL"} {error "via9 missing"}
set f [open $package/expected-bpins.tsv];set nets {};set expected {}
while {[gets $f line]>=0} {
 set a [split $line "\\t"];lassign $a port netname ln x1 y1 x2 y2
 set bt [$block findBTerm $port]
 if {$bt eq "NULL" || [[$bt getNet] getName] ne $netname} {error "Expected port/net changed $port"}
 set actual {}
 foreach bp [$bt getBPins] {foreach box [$bp getBoxes] {lappend actual [list $port $netname [[$box getTechLayer] getName] [$box xMin] [$box yMin] [$box xMax] [$box yMax]]}}
 if {$actual ne [list $a]} {error "Expected exact port geometry changed $port"}
 dict set nets $netname [$bt getNet]
 lappend expected $a
}
close $f
if {[dict size $nets]!=4} {error "Expected four nets"}
set rectangles {{1953690 2348140 1953890 2349740} {3124890 2348140 3125090 2349740}}
set present {}
foreach ob [$block getObstructions] {set box [$ob getBBox];dict set present [list [[$box getTechLayer] getName] [$box xMin] [$box yMin] [$box xMax] [$box yMax]] 1}
set added 0
foreach rect $rectangles {
 set key [linsert $rect 0 via9]
 if {[dict exists $present $key]} {continue}
 lassign $rect x1 y1 x2 y2
 ::odb::dbObstruction_create $block $layer $x1 $y1 $x2 $y2
 incr added
}
set f [open external-via9-ripped.tsv a];set ripped 0
foreach name [dict keys $nets] {set net [dict get $nets $name];if {[$net getWire] ne "NULL"} {::odb::dbWire_destroy [$net getWire];puts $f $name;incr ripped}}
close $f
puts "C_EXTERNAL_VIA9_VIRTUAL_GUARD added=$added ripped=$ripped"
}
''')
(p/'probe.tcl').write_text('''set_thread_count 8
read_db /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/runs/C-v27-joint-e20-h30/flow/results/nangate45/c-overlay-current/base/6_final.odb
source /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/C-final-v1/geometry-all.tcl
set before [geometry_snapshot before-geometry.tsv]
write_verilog before.v
source hook.tcl
if {$::c_external_via9_guard::added!=2 || $::c_external_via9_guard::ripped!=4} {error "Expected initial 2 keepouts / 4 ripped wires"}
source hook.tcl
if {$::c_external_via9_guard::added!=0 || $::c_external_via9_guard::ripped!=0} {error "Guard not idempotent"}
write_verilog after.v
exec cmp before.v after.v
if {[geometry_snapshot after-geometry.tsv] ne $before} {error "Boundary geometry changed"}
puts EXTERNAL_VIA9_STRUCTURAL_PASS
set_routing_layers -signal metal2-metal10 -clock metal4-metal10
pin_access -via_in_pin_bottom_layer metal10 -via_in_pin_top_layer metal10 -via_access_layer metal10 -verbose 1
puts EXTERNAL_VIA9_STATIC_ACCESS_PASS_REQUIRES_ACTUAL_ROUTE
''')
s=(r/'audit/C-v27-r-fullguard/probe.sbatch').read_text().replace('C-v27-r-fullguard','C-v27-external-via9-guard');(p/'probe.sbatch').write_text(s)
