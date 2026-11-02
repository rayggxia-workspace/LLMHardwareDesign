"""GDS-exact M3 obstructions, preserving every pin and other LEF byte.
Signal landing-metal components are identified on actual M3, pairwise isolated,
and excluded from OBS alongside PG port windows. No masks or circuits change.
Run allocated KLayout with GDS/LEF/OUTPUT/RECEIPT -rd arguments.
"""
import pya,re,json,hashlib,os
from pathlib import Path
assert os.environ.get('SLURM_JOB_ID');out=Path(OUTPUT).parent;gds=Path(GDS);lef=Path(LEF);assert not Path(OUTPUT).exists();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
l=pya.Layout();l.read(str(gds));assert l.dbu==.0005
actual=pya.Region(l.top_cell().begin_shapes_rec(l.find_layer(15,0))).merged();text=lef.read_text();ports=pya.Region();signal=pya.Region();names=[]
rect=r'RECT\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s*;'
def region(s):
 r=pya.Region()
 for m in re.finditer(rect,s):r.insert(pya.Box(*[round(float(x)*2000)for x in m.groups()]))
 return r.merged()
for pin in re.finditer(r'(?ms)^\s*PIN\s+(\S+)\s*\n(.*?)^\s*END\s+\1\s*$',text):
 for part in re.finditer(r'(?s)LAYER\s+metal3\s*;(.*?)(?=\bLAYER\b|\bEND\b|\Z)',pin.group(2)):
  window=region(part.group(1));assert (window-actual).is_empty();ports+=window
  if pin.group(1)not in ['vdd','gnd']:
   connected=actual.interacting(window);assert connected.count()==1 and (connected&signal).is_empty();signal+=connected;names.append(pin.group(1))
ports=(ports|signal).merged();replacement=(actual-ports).merged();assert (actual-(replacement|ports)).is_empty()
obs=list(re.finditer(r'(?ms)^\s*OBS\s*\n(.*?)^\s*END\s*$',text));assert len(obs)==1
parts=list(re.finditer(r'(?s)LAYER\s+metal3\s*;(.*?)(?=\bLAYER\b|\Z)',obs[0].group(1)));assert len(parts)==1;m=parts[0];old=region(m.group(1))
boxes=[]
for p in replacement.decompose_trapezoids_to_region().each():
 assert p.is_box();bb=p.bbox();boxes.append((bb.left,bb.bottom,bb.right,bb.top))
geometry='\n'+''.join('    RECT '+' '.join(format(x*.0005,'.4f')for x in a)+' ;\n'for a in sorted(boxes))+'    '
assert (region(geometry)^replacement).is_empty()
start=obs[0].start(1)+m.start(1);end=obs[0].start(1)+m.end(1);result=text[:start]+geometry+text[end:];Path(OUTPUT).write_text(result)
Path(RECEIPT).write_text(json.dumps(dict(passed=True,qualified=False,inputs={str(p):sha(p)for p in [gds,lef]},output=str(Path(OUTPUT)),output_sha256=sha(Path(OUTPUT)),dbu_um=l.dbu,serialized_geometry_exact=True,rectangles=len(boxes),signal_pin_connected_components=len(names),same_layer_signal_components_pairwise_disjoint=True,only_metal3_obs_changed=True,all_actual_m3_covered_by_obstructions_or_proven_pin_connected_metal=True,old_missing_area_dbu2=(actual-(old|ports)).area(),old_false_obstruction_area_dbu2=(old-actual).area(),unchanged_prefix_sha256=hashlib.sha256(text[:start].encode()).hexdigest(),unchanged_suffix_sha256=hashlib.sha256(text[end:].encode()).hexdigest()),indent=2)+'\n')
print(Path(RECEIPT).read_text())
