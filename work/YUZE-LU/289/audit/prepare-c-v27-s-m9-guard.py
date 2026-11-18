from pathlib import Path
import json, hashlib
r=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117')
p=r/'audit/C-v27-s-m9-guard'
p.mkdir(exist_ok=False)
source=r/'audit/C-v27-physical/non-dot-upper-net-candidates.json'
markers=[m for m in json.loads(source.read_text()) if m['id'] in (7,9)]
assert len(markers)==2
assert all(m['category']=="'METAL9.2'" for m in markers)
(p/'source-markers.json').write_text(json.dumps(markers,indent=2))
(p/'hook.tcl').write_text(r'''# Virtual routing obstruction in the actual empty gap; no physical metal edit.
namespace eval ::c_s_m9_guard {
set block [::ord::get_db_block]
set tech [[::ord::get_db] getTech]
if {[$tech getDbUnitsPerMicron]!=2000} {error "Unexpected DBU"}
set layer [$tech findLayer metal9]
set n [$block findNet net52834]
if {$n eq "NULL" || [llength [$n getBTerms]]!=0} {error "Expected internal net52834"}
set macro [$block findInst services.store.leaf]
if {$macro eq "NULL"} {error "Missing fixed S macro"}
set rect {2722800 223340 2723000 228140}
set found 0
foreach ob [$block getObstructions] {
 set bb [$ob getBBox]
 if {[[$bb getTechLayer] getName] eq "metal9" && [list [$bb xMin] [$bb yMin] [$bb xMax] [$bb yMax]] eq $rect} {set found 1}
}
set added 0
if {!$found} {lassign $rect x1 y1 x2 y2;::odb::dbObstruction_create $block $layer $x1 $y1 $x2 $y2;set added 1}
set ripped 0
if {[$n getWire] ne "NULL"} {::odb::dbWire_destroy [$n getWire];set ripped 1}
puts "C_S_M9_GUARD added=$added ripped=$ripped"
}
''')
(p/'probe.tcl').write_text(f'''set_thread_count 8
read_db {r}/cu/runs/C-v27-joint-e20-h30/flow/results/nangate45/c-overlay-current/base/6_final.odb
source {r}/audit/C-final-v1/geometry-all.tcl
set before [geometry_snapshot before-geometry.tsv]
write_verilog before.v
source hook.tcl
if {{$::c_s_m9_guard::added!=1 || $::c_s_m9_guard::ripped!=1}} {{error "Expected one new guard / one rip"}}
source hook.tcl
if {{$::c_s_m9_guard::added!=0 || $::c_s_m9_guard::ripped!=0}} {{error "Not idempotent"}}
write_verilog after.v
exec cmp before.v after.v
if {{[geometry_snapshot after-geometry.tsv] ne $before}} {{error "Geometry changed"}}
write_db dry-edit.odb
puts C_S_M9_STRUCTURAL_PASS
set_routing_layers -signal metal2-metal10 -clock metal4-metal10
pin_access -via_in_pin_bottom_layer metal10 -via_in_pin_top_layer metal10 -via_access_layer metal10 -verbose 1
puts C_S_M9_STATIC_ACCESS_PASS_REQUIRES_ACTUAL_ROUTE
''')
batch=(r/'audit/C-v27-external-via9-guard/probe.sbatch').read_text().replace('C-v27-external-via9-guard','C-v27-s-m9-guard')
(p/'probe.sbatch').write_text(batch)
(p/'manifest.json').write_text(json.dumps(dict(accepted=False,scope='Trial virtual M9 guard; exact main markers 7/9; needs actual reroute and complete verification',source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),guard_dbu=[2722800,223340,2723000,228140],ripped_internal_net='net52834',original_gap_um=.605,original_rule_um=.8),indent=2))
