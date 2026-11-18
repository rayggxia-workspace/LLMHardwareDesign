from pathlib import Path
import json,hashlib,shutil,collections
r=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117');pkg=r/'audit/C-antenna-v27-r2';src=r/'audit/C-final-v1/antenna-C-v27-joint-e20-h30-120037'
rows=json.loads((src/'mapped-net-inventory.json').read_text());summary=json.loads((src/'summary.json').read_text());mapping=json.loads((src/'antenna-net-map.json').read_text());assert mapping['mapping_complete'] and len(rows)==17 and summary['all_mapped_top_ports_are_inputs']
assert hashlib.sha256((src/'antenna-net-map.json').read_bytes()).hexdigest()==summary['mapping_sha256']
for p,h in mapping['source_sha256'].items():
 q=Path(p)
 if not q.is_absolute():q=src/q;assert q.resolve().parent==src.resolve()
 assert hashlib.sha256(q.read_bytes()).hexdigest()==h,p
assert all(x['top_ports'] and not x['selected_output_ports'] and not x['existing_parent_diodes'] and set(x['top_port_directions'].values())=={'INPUT'} for x in rows)
def brace(s):
 assert not any(c in s for c in '{}\n\r\t'),s
 return '{'+s+'}'
ordered=sorted(rows,key=lambda x:x['net']);lines=['# Frozen source-observed input-port/net associations; NO anchor names or coordinates.','set c_ant_plan {'];plan=[]
for i,row in enumerate(ordered):
 name='i289_c_ant17_'+str(i);ports=sorted(row['top_ports']);plan.append(dict(net=row['net'],input_ports=ports,diode=name));lines.append('  {'+brace(row['net'])+' {'+' '.join(brace(p) for p in ports)+'} '+brace(name)+'}')
lines.append('}')
for name in ('plan.tcl','plan.json','manifest.json','selected-outputs.txt'):assert not (pkg/name).exists(),name
(pkg/'plan.tcl').write_text('\n'.join(lines)+'\n');(pkg/'plan.json').write_text(json.dumps(plan,indent=2));shutil.copyfile(r/'cu/C-outputs.txt',pkg/'selected-outputs.txt');shutil.copyfile(r/'audit/C-final-v1/geometry-all.tcl',pkg/'geometry-all.tcl');shutil.copyfile(r/'audit/U-antenna/diode-model.json',pkg/'qualified-diode-model.json')
selected=set((pkg/'selected-outputs.txt').read_text().splitlines());assert len(selected)==153
portnets={}
for s in (src/'bpins.tsv').read_text().splitlines():
 p,n,*_=s.split('\t')
 if p in selected:portnets[n]=p
classes=collections.Counter()
for s in (src/'endpoints.tsv').open():
 n,inst,m,p,d,*_=s.rstrip('\n').split('\t')
 if n in portnets and d=='OUTPUT':classes[m]+=1
assert sum(classes.values())==153;print('SOURCE_SELECTED_DRIVER_CLASSES',dict(classes))
files=[src/'antenna-net-map.json',src/'mapped-net-inventory.json',src/'summary.json',r/'audit/C-v27-physical/focused/antenna-binding.json',r/'cu/C-outputs.txt']+list(pkg.glob('*.tcl'))+[pkg/'plan.json',pkg/'selected-outputs.txt',pkg/'qualified-diode-model.json',Path(__file__)]
v=dict(scope='Trial17 actual-source INPUT nets, one ANTENNA_X1 per net; dynamic actual-candidate receiving-pin anchors; no borrowed coordinates. No routed/timing/manufacturing acceptance.',observed_source_gds_sha256='cc3f80b43858fb882d9d2d391edfd73b40921f3ccb221c6c15a2c69ea6702a58',source_mapping_sha256=summary['mapping_sha256'],plan_count=17,selected_output_count=153,source_selected_driver_classes=dict(classes),anchor_policy='Nearest current placed standard-cell INPUT pin to current BPin geometry, deterministic tie-break by actual instance/pin names. Audited fallback to current instance origin only if pin geometry absent; placement left of anchor only at right core edge. No standard receiver => fail before edits.',source_sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in files})
(pkg/'manifest.json').write_text(json.dumps(v,indent=2));print(pkg/'manifest.json')
