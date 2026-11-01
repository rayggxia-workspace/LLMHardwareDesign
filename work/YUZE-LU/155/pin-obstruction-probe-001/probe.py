import pya,re,json,hashlib,os
from pathlib import Path
assert os.environ.get('SLURM_JOB_ID')
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-155')
gds=b/'bank-eco-001/s_sram_256x128_freepdk45.gds'
lef=b/'generate-007/generation/bank/s_sram_256x128_freepdk45.lef'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
before={str(p):sha(p) for p in [gds,lef]}
l=pya.Layout();l.read(str(gds));assert l.dbu==0.0005
real=pya.Region(l.top_cell().begin_shapes_rec(l.find_layer(17,0)))
text=lef.read_text();obs=re.search(r'(?ms)^\s*OBS\s*\n(.*?)^\s*END\s*$',text).group(1)
part=re.search(r'(?s)LAYER\s+metal4\s*;(.*?)(?=\bLAYER\b|\Z)',obs).group(1)
def box(v):return pya.Box(*[round(float(x)/l.dbu) for x in v])
rect=r'RECT\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s*;'
abstract=pya.Region()
for m in re.finditer(rect,part):abstract.insert(box(m.groups()))
pins=[]
for m in re.finditer(r'(?ms)^\s*PIN\s+(\S+)\s*\n(.*?)^\s*END\s+\1\s*$',text):
 name,body=m.groups()
 if 'USE POWER' in body or 'USE GROUND' in body:continue
 regions=[]
 for q in re.finditer(r'(?s)LAYER\s+metal3\s*;(.*?)(?=\bLAYER\b|\bEND\b|\Z)',body):
  for z in re.finditer(rect,q.group(1)):regions.append(pya.Region(box(z.groups())))
 for region in regions:
  pins.append(dict(name=name,projection_dbu=region.bbox().to_s(),m4_abstract_covers_projection=(region-abstract).is_empty(),real_m4_intersects_projection=not (region&real).is_empty()))
assert pins and all(sha(Path(p))==h for p,h in before.items())
r=dict(qualified=False,scope='Geometric vertical-access diagnostic of old 9-stage bank only, not a routed pin-access failure or new49 bank qualification',inputs=before,metal4_gds_layer=[17,0],dbu_um=l.dbu,metal3_signal_pin_regions=len(pins),blocked_by_abstract_but_no_real_m4=sum(p['m4_abstract_covers_projection'] and not p['real_m4_intersects_projection'] for p in pins),pins=pins)
Path(OUTPUT).write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items() if k!='pins'},indent=2))
