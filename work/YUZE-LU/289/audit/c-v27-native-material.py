from pathlib import Path
import re,json,hashlib,collections,pya
r=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117')
p=r/'audit/C-v27-native-material';p.mkdir(exist_ok=False)
g=r/'cu/runs/C-v27-joint-e20-h30/flow/results/nangate45/c-overlay-current/base/6_final.gds'
n=r/'audit/C-v27-m10/reroute-v2/native-before.rpt'
hashes={str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in (g,n)}
l=pya.Layout();l.read(str(g));assert l.dbu==.0001
rows=re.findall(r'violation type: (.*?)\n\s*srcs: (.*?)\n\s*bbox = (.*?) on Layer (\S+)',n.read_text())
assert len(rows)==232
layers={'metal2':(13,.07),'metal3':(15,.07),'metal9':(27,.8),'metal10':(29,.8),'via9':(28,.88)}
out=[]
for idx,(kind,src,box,layer) in enumerate(rows):
 xy=list(map(float,re.findall(r'-?\d+\.\d+',box)));assert len(xy)==4
 marker=pya.Box(*[round(x*10000) for x in xy]);roi=marker.enlarged(20000)
 li,spacing=layers[layer]
 actual=pya.Region(l.top_cell().begin_shapes_rec_overlapping(l.layer(li,0),roi))&pya.Region(roi);actual.merge()
 checks={}
 for name,ep in [('space',actual.space_check(round(spacing*10000))),('notch',actual.notch_check(round(spacing*10000)))]:
  hits=[]
  for pair in ep.each():
   if pair.bbox().touches(marker):hits.append(str(pair))
  checks[name]=hits
 rec=dict(index=idx,kind=kind,source=src,layer=layer,bbox_um=xy,
          marker_fully_covered_by_actual_metal=(pya.Region(marker)-actual).is_empty(),
          actual_rule_spacing_um=spacing,actual_local_check=checks)
 out.append(rec)
 if idx%25==0:print('COMPLETE',idx,flush=True)
assert hashes=={str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in (g,n)}
result=dict(accepted=False,scope='Diagnostic mapping of fresh native markers to actual merged GDS material. Local original minimum spacing/notch checks are not the complete original deck or connectivity verification.',hashes=hashes,count=len(out),by_layer=dict(collections.Counter(x['layer'] for x in out)),fully_metal_covered=sum(x['marker_fully_covered_by_actual_metal'] for x in out),no_local_spacing_or_notch=sum(not any(x['actual_local_check'].values()) for x in out),markers=out)
(p/'receipt.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items() if k!='markers'},indent=2))
