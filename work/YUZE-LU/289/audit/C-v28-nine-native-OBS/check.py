"""Marker-specific conservative OBS diagnosis; never signoff or a waiver."""
from pathlib import Path
import pya,re,ast,json,hashlib
r=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117');p=Path.cwd();source=r/'audit/C-v28-nine-net-combined-v1';classify=r/'audit/C-v28-nine-native-classification/classification/receipt.json';guard=r/'audit/C-v27-r-fullguard';leaf=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-166-r-local-state/attempt252/delivery/native')
parser=r/'audit/C-v27-rcx-normalization-v2/parser-source.py';sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
files=[source/'patched.odb',source/'patched.def',source/'patched.gds',source/'native-after.rpt',classify,leaf/'6_final.def',leaf/'6_final.gds',leaf/'6_final.odb',parser,guard/'keepout.tsv',guard/'master-geometry.tsv',guard/'receipt.json',guard/'derive.py',p/'parent-obs.tsv',p/'parent-layers.tsv',p/'parent-vias.tsv',p/'leaf-layers.tsv',p/'leaf-vias.tsv',p/'leaf-readback.def',p/'parent.tcl',p/'leaf.tcl',Path(__file__)]
before={str(f):sha(f) for f in files}
receipt=json.loads(classify.read_text());rows=[x for x in receipt['markers'] if x['disposition']=='unresolved'];assert rows
assert receipt['inputs_sha256'][str(source/'patched.def')]==sha(source/'patched.def') and receipt['inputs_sha256'][str(source/'patched.gds')]==sha(source/'patched.gds')
origin=(144000,144000);transform=pya.Trans(720000,720000)
layout=pya.Layout();layout.read(str(source/'patched.gds'));assert layout.dbu==.0001
standalone=pya.Layout();standalone.read(str(leaf/'6_final.gds'));assert standalone.dbu==.0001
actual_local=pya.Region(layout.cell('r_stream_local').begin_shapes_rec(layout.layer(27,0))).merged()
source_local=pya.Region(standalone.cell('r_stream_local').begin_shapes_rec(standalone.layer(27,0))).merged()
assert (actual_local^source_local).is_empty(), 'Merged actual R M9 differs from frozen leaf source'
actual=actual_local.transformed(transform)
old_obs=pya.Region();die=None
for line in (guard/'master-geometry.tsv').read_text().splitlines():
 a=line.split('\t')
 if a[0]=='MASTER':die=list(map(int,a[2:]));continue
 if a[0]=='OBS' and a[2]=='metal9':old_obs.insert(pya.Box(*[int(v)*5 for v in a[3:7]]))
assert die
keepout=pya.Region()
for line in (guard/'keepout.tsv').read_text().splitlines():
 name,layer,*box=line.split('\t');assert name=='r_stream_local'
 if layer=='metal9':keepout.insert(pya.Box(*[int(v)*5 for v in box]))
expected=(actual_local.sized(4000)-old_obs)&pya.Region(pya.Box(0,0,die[0]*5,die[1]*5))
assert (expected^keepout).is_empty(), 'Guard no longer equals actual R material expansion minus prior OBS'
installed=pya.Region()
for line in (p/'parent-obs.tsv').read_text().splitlines():installed.insert(pya.Box(*[int(v)*5 for v in line.split('\t')]))
assert (installed^(old_obs+keepout).transformed(transform)).is_empty(), 'Unaccounted actual installed M9 OBS'
def parse_factory(label):
 width={n:int(w) for n,w in (s.split('\t') for s in (p/(label+'-layers.tsv')).read_text().splitlines())};vias={};vlayers={}
 for s in (p/(label+'-vias.tsv')).read_text().splitlines():
  n,l,*b=s.split('\t');vias.setdefault(n,[]).append((l,list(map(int,b))))
  if l.startswith('metal'):vlayers.setdefault(n,set()).add(l)
 tree=ast.parse(parser.read_text());fn=next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='parse')
 env=dict(pya=pya,re=re,width=width,vias=vias,vlayers=vlayers,fmt=lambda pt,e:'( '+str(pt[0])+' '+str(pt[1])+(' '+str(e) if e is not None else '')+' )')
 exec(compile(ast.Module(body=[fn],type_ignores=[]),str(parser),'exec'),env);return env['parse']
def bodies(path):
 text=path.read_text().split('\nNETS ',1)[1].split('\nEND NETS',1)[0]
 return {m[1]:m[2] for m in re.finditer(r'^\s*-\s+(\S+)\s+(.*?);\s*$',text,re.M|re.S)}
parent_parse=parse_factory('parent');leaf_parse=parse_factory('leaf');parent_bodies=bodies(source/'patched.def');leaf_bodies=bodies(leaf/'6_final.def');readback=bodies(p/'leaf-readback.def')
scale=pya.ICplxTrans(5,0,False,0,0);results=[]
for row in rows:
 assert row['layer']=='metal9' and row['kind']=='Metal Spacing'
 m=re.fullmatch(r'inst:services.engine\\\[2\\\].genblk1.recurrent.leaf.leaf net:(\S+)',row['source']);assert m,row['source'];name=m[1]
 body=parent_bodies[name];parent=parent_parse(body)[0]['metal9'].transformed(scale)
 ownpin=re.findall(r'\(\s*services.engine\\\[2\\\].genblk1.recurrent.leaf.leaf\s+(\S+)\s*\)',body.split('+ ROUTED')[0]);assert len(ownpin)<=1
 own=pya.Region()
 if ownpin:
  a=leaf_parse(leaf_bodies[ownpin[0]])[0].get('metal9',pya.Region());b=leaf_parse(readback[ownpin[0]])[0].get('metal9',pya.Region());assert (a^b).is_empty()
  own=a.transformed(scale).transformed(transform)
 box=pya.Box(*[round(v*10000) for v in row['bbox_um']]);roi=pya.Region(box.enlarged(20000))
 target=parent&roi;real=actual&roi;own&=roi;assert (own-real).is_empty()
 allmetal=pya.Region(layout.top_cell().begin_shapes_rec_overlapping(layout.layer(27,0),box.enlarged(20000)))&roi;allmetal.merge();assert (target-allmetal).is_empty()
 foreign=real-own
 overlap=(target&foreign).area();same_overlap=(target&own).area()
 sep=[str(e) for e in target.separation_check(foreign,8000).each() if e.bbox().touches(box)]
 ownsep=[str(e) for e in target.separation_check(own,8000).each() if e.bbox().touches(box)]
 checks={n:[str(e) for e in test(8000).each() if e.bbox().touches(box)] for n,test in [('space',allmetal.space_check),('notch',allmetal.notch_check),('width',allmetal.width_check)]}
 virtual=[str(e) for e in target.separation_check(installed&roi,8000).each() if e.bbox().touches(box)]
 addedguard=keepout.transformed(transform)&roi
 guard_pairs=[str(e) for e in target.separation_check(addedguard,8000).each() if e.bbox().touches(box)]
 assert overlap==0 and not sep and not any(checks.values()), (row['index'],overlap,sep,checks)
 assert virtual and guard_pairs, ('Could not reproduce conservative guard spacing',row['index'])
 results.append(dict(index=row['index'],source=row['source'],bbox_um=row['bbox_um'],leaf_same_net=ownpin or [],all_other_actual_leaf_material_treated_as_foreign=True,foreign_overlap_um2=overlap*1e-8,own_overlap_um2=same_overlap*1e-8,foreign_spacing800nm=sep,own_spacing800nm=ownsep,actual_global_local_checks=checks,installed_OBS_spacing800nm=virtual,added_guard_spacing800nm=guard_pairs,diagnosis='Exact actual leaf M9 is clear under original rules; native spacing reproduced against the proven additional 0.4um virtual guard. Root disposition and same-final-GDS full deck zero remain required.'))
 assert before=={str(f):sha(f) for f in files}
result=dict(accepted=False,diagnostic_passed=True,scope='Candidate-specific five-or-other-count native macro OBS diagnostic; no waiver and no automatic future reuse.',count=len(results),actual_source_leaf_M9_exact=True,installed_OBS_exact_old_plus_actual_400nm_guard=True,markers=results,hashes=before)
(p/'receipt.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
