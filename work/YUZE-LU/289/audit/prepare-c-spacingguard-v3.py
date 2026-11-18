from pathlib import Path
r=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117');old=r/'audit/C-upper-metal-guard-v2';p=r/'audit/C-upper-spacing-guard-v3';p.mkdir(exist_ok=False)
s=(old/'export.tcl').read_text().replace('{r_stream_local local_s_base}','{r_stream_local local_s_base block_v2_g block_v2_e_compact}').replace('{metal7 metal8 metal9 metal10}','{metal7 metal8 metal9 metal10 via7 via8 via9}');(p/'export.tcl').write_text(s)
(p/'derive.py').write_text('''from pathlib import Path
import pya,json,hashlib,collections
p=Path.cwd();r=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117');g=r/'cu/runs/C-v20-native-clock4/flow/results/nangate45/c-overlay-current/base/6_final.gds';l=pya.Layout();l.read(str(g));assert l.dbu==0.0001
loc=json.loads((r/'audit/C-main-clock4-physical-v1/non-dot-upper-net-candidates.json').read_text());allloc=json.loads((r/'audit/C-main-clock4-physical-v1/upper-localization.json').read_text());macros={m['name']:m for m in allloc['macro_instances']};regions={};sizes={}
for s in (p/'master-geometry.tsv').read_text().splitlines():
 a=s.split('\\t')
 if a[0]=='MASTER':sizes[a[1]]=list(map(int,a[2:]));continue
 k,n,layer,*v=a;regions.setdefault((k,n,layer),pya.Region()).insert(pya.Box(*[int(z)*5 for z in v[:4]]))
clips={};ids=collections.defaultdict(list);unaddressed=[]
for m in loc:
 if len(m['macro'])!=1:unaddressed.append(m);continue
 n=m['macro'][0];layer=m['category'].strip("'").split('.')[0].lower();assert layer in ('metal9','metal10','via9');o=macros[n];a,b,c,d=m['bbox_um'];clips.setdefault((n,layer),pya.Region()).insert(pya.Box(round((a-o['dx_um']-1)*10000),round((b-o['dy_um']-1)*10000),round((c-o['dx_um']+1)*10000),round((d-o['dy_um']+1)*10000)));ids[n,layer].append(m['id'])
rows=[];stats=[]
for (n,layer),clip in sorted(clips.items()):
 num={'metal9':27,'metal10':29,'via9':28}[layer];actual=pya.Region(l.cell(n).begin_shapes_rec(l.layer(num,0))).merged();obs=regions.get(('OBS',n,layer),pya.Region());pins=regions.get(('PIN',n,layer),pya.Region());expanded=(actual&clip).sized(4000);keepout=(expanded-obs-pins).merged();recovered=pya.Region();count=0
 for poly in keepout.decompose_trapezoids_to_region().each():
  b=poly.bbox();assert b.area()==poly.area();v=[b.left,b.bottom,b.right,b.top];assert all(z%5==0 for z in v);assert b.left>=0 and b.bottom>=0 and b.right<=sizes[n][0]*5 and b.top<=sizes[n][1]*5;rows.append((n,layer,*[z//5 for z in v]));recovered.insert(b);count+=1
 assert (recovered^keepout).is_empty() and (keepout&pins).is_empty();stats.append(dict(master=n,layer=layer,marker_ids=ids[n,layer],rectangles=count,added_keepout_um2=keepout.area()*1e-8,port_exemption_um2=(expanded&pins).area()*1e-8))
(p/'keepout.tsv').write_text(''.join('\\t'.join(map(str,x))+'\\n' for x in rows));nets=sorted({h['net'] for m in loc for h in m['hits']});(p/'ripup-nets.txt').write_text('\\n'.join(nets)+'\\n');v=dict(scope='Localized 0.4um routing keepout expansion around actual macro metal/cuts at actual main upper-rule violation sites; subtract installed OBS and exact actual MPins. Conservative routing constraint only, no physical metal/pin edit. Port-exempt and exterior sites still require actual postroute recheck.',stats=stats,rectangles=len(rows),all_22_target_parent_nets=nets,macro_exterior_unaddressed=unaddressed,source_sha256={str(q):hashlib.sha256(q.read_bytes()).hexdigest() for q in [g,p/'master-geometry.tsv',p/'keepout.tsv',p/'ripup-nets.txt',Path(__file__)]});(p/'receipt.json').write_text(json.dumps(v,indent=2));print(json.dumps(v,indent=2))
''')
s=(old/'run.sbatch').read_text().replace('C-upper-metal-guard-v2','C-upper-spacing-guard-v3');(p/'run.sbatch').write_text(s)
