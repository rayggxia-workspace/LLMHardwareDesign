from pathlib import Path
import json,hashlib
root=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117');out=root/'audit/U-antenna/guard-v1-map';m=json.loads((out/'antenna-net-map.json').read_text());assert not m['ambiguous'] and not m['unmapped'];plans=m['plans'];assert len({p['net'] for p in plans})==len(plans)
def quote(s):
 assert not any(c in s for c in '{}\n\r');return '{'+s+'}'
rows=[]
for i,p in enumerate(sorted(plans,key=lambda p:p['net'])):
 assert not p['existing_diodes'];a=p['anchor'];rows.append('  {'+' '.join(map(quote,[p['net'],a['instance'],a['pin'],'i289_foundry_ant_r2_'+str(i)]))+'}')
script='''# Source after loading the CURRENT spacing-clean candidate; no original file is mutated.
# Exact guard+antenna v1 residual foundry-antenna net map. Stop on any topology mismatch; do not fall back.
set block [ord::get_db_block]
set master [[ord::get_db] findMaster ANTENNA_X1]
if {$master eq "NULL"} {error "Missing verified ANTENNA_X1 master"}
set plan {\n'''+ '\n'.join(rows)+'''\n}
# Validate the complete plan before editing anything.
foreach spec $plan {
 lassign $spec netname anchorname pinname newname
 set net [$block findNet $netname];set anchor [$block findInst $anchorname]
 if {$net eq "NULL" || $anchor eq "NULL"} {error "Antenna anchor missing: $spec"}
 set term [$anchor findITerm $pinname]
 if {$term eq "NULL" || [$term getNet] ne $net} {error "Antenna anchor topology changed: $spec"}
 if {[$block findInst $newname] ne "NULL"} {error "Antenna instance already exists $newname"}
 foreach t [$net getITerms] {
  if {[[[$t getInst] getMaster] getName] eq "ANTENNA_X1"} {error "Existing diode needs separate physical review: $netname"}
 }
}
set log [open antenna-insertions.tsv w]
foreach spec $plan {
 lassign $spec netname anchorname pinname newname
 set net [$block findNet $netname];set anchor [$block findInst $anchorname]
 lassign [$anchor getLocation] x y
 set diode [odb::dbInst_create $block $master $newname]
 $diode setOrient [$anchor getOrient]
 $diode setLocation [expr {$x+[[$anchor getMaster] getWidth]}] $y
 $diode setPlacementStatus PLACED
 [$diode findITerm A] connect $net
 foreach rail {VDD VSS} {[$diode findITerm $rail] connect [$block findNet $rail]}
 puts $log "$netname\\t$newname\\t$anchorname\\t$pinname\\t$x\\t$y"
}
close $log
puts "FOUNDRY_ANTENNA_DIODES_INSERTED [llength $plan]; legalization, affected-net routing, extraction, fresh STA, PG, antenna and full foundry GDS signoff still required"
'''
p=out/'insert-diodes-v2.tcl';p.write_text(script)
r=dict(accepted=False,scope='Prepared pure DB edit only; requires physical and functional qualification after integration',selected_net_count=len(plans),diode='ANTENNA_X1',pin='A',source_map_sha256=hashlib.sha256((out/'antenna-net-map.json').read_bytes()).hexdigest(),script_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),plans=[dict(net=p['net'],anchor=p['anchor'],marker_count=len(p['markers'])) for p in plans])
(out/'diode-insertion-plan.json').write_text(json.dumps(r,indent=2));print('Prepared',len(plans),'exact diodes',r['script_sha256'])

print(json.dumps([p["net"] for p in plans],indent=2))
