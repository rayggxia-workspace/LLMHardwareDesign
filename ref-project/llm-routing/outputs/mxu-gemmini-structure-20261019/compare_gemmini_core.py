"""Read existing Gemmini source/cone evidence at a broader core cut; no RTL edits."""
from pathlib import Path
import collections,gzip,hashlib,json,subprocess
D=Path(__file__).parent
code=r'''
from pathlib import Path
import collections,gzip,hashlib,json
R=Path('/public/home/yuzelu/project-circuit/llm_routing_analysis')
P=R/'stats/gemmini-4x4-v1/dedicated_v2/nets.jsonl.gz'
C=R/'tables/gemmini_4x4_receiver_cones_v1/cell_cones.jsonl.gz'
norm=lambda s:s.replace('\\[','[').replace('\\]',']')
def role(m):
 if m=='MESH_PIPELINE' or m.startswith('COMPUTE_PE:'):return 'INTEGER_CORE'
 return {'SHIFT_DELAY':'IO_ALIGNMENT','TRANSPOSE':'IO_ALIGNMENT','TAG_QUEUE':'CONTROL_METADATA','TOTAL_ROWS_QUEUE':'CONTROL_METADATA'}.get(m)
def recs(p):
 with gzip.open(p,'rt') as f:
  for line in f:yield json.loads(line)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
cones={}
for r in recs(C):
 if r['status'] in ('EXCLUSIVE','SHARED'):
  rs={role(g) for g in r['groups']}
  if None not in rs and len(rs)==1:cones[norm(r['cell'])]=(r['master'],next(iter(rs)))
allstat={'nets':0,'length_dbu':0,'layers':{}};classes={};internals={};pairs={};known={};scope=set()
def add(tab,k,r):
 z=tab.setdefault(k,{'nets':0,'length_dbu':0,'layers':{}});z['nets']+=1;z['length_dbu']+=r.get('length_dbu') or 0
 for l,v in r.get('layers',{}).items():z['layers'][l]=z['layers'].get(l,0)+v['length_dbu']
for r in recs(P):
 if r.get('sig_type') in ('POWER','GROUND'):continue
 gs=set();bad=False;top=False
 for e in r['endpoints']:
  if e.get('master_type') in ('CORE_SPACER','CORE_WELLTAP','CORE_ANTENNACELL'):continue
  if e['kind']=='BTERM':top=True;continue
  n=norm(e['instance']);g=role(e.get('module','UNKNOWN'))
  if g:known[n]=(g,'SOURCE')
  elif n in cones:
   assert cones[n][0]==e['master'];g=cones[n][1];known[n]=(g,'EXCLUSIVE_ROLE_SERVICE')
  if g:gs.add(g)
  else:bad=True
 if r.get('sig_type')=='CLOCK' or r.get('category') in ('CLOCK','RESET'):cls='CLOCK_RESET'
 elif top:cls='TOP_INTERFACE'
 elif bad:cls='PARTIAL_CROSS' if len(gs)>1 else 'UNRESOLVED'
 elif len(gs)>1:cls='COMPLETE_CROSS'
 else:cls='COMPLETE_INTERNAL'
 add(classes,cls,r)
 if cls=='COMPLETE_INTERNAL' and len(gs)==1:add(internals,next(iter(gs)),r)
 if cls=='COMPLETE_CROSS':add(pairs,' + '.join(sorted(gs)),r)
 allstat['nets']+=1;allstat['length_dbu']+=r.get('length_dbu') or 0
 for l,v in r.get('layers',{}).items():allstat['layers'][l]=allstat['layers'].get(l,0)+v['length_dbu']
assert sum(v['length_dbu'] for v in classes.values())==allstat['length_dbu']
for l,v in allstat['layers'].items():assert sum(z['layers'].get(l,0) for z in classes.values())==v
print(json.dumps({'units':1000,'all':allstat,'classes':classes,'internal_groups':internals,'complete_cross_sets':pairs,'classified_cells':dict(collections.Counter(g for g,ev in known.values())),'nets_sha256':sha(P),'cones_sha256':sha(C),'method':'PE + MESH_PIPELINE core; SHIFT_DELAY + TRANSPOSE kept jointly as bidirectional IO_ALIGNMENT, not forced into input/output. Source labels precede exclusive broad-role service. Shared fine groups may resolve to one broad role only when their cone is fully closed.'}))
'''
p=subprocess.run(['ssh','-o','BatchMode=yes','10.129.166.172','/public/home/yuzelu/miniconda3-pbit/bin/python3','-'],input=code.encode(),stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True)
x=json.loads(p.stdout)
(D/'gemmini_core_comparison.json').write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(x['internal_groups'],ensure_ascii=False))
