"""Read-only lower-overlay collision replay; execute on allocated node after final export.
Config supplies rules_dir, native_gz, ports_tsv, overlay_json, block,
native_transform=[sx,dx,sy,dy], overlay_transform=[sx,dx,sy,dy], output.
Only verifies the legacy M7-M10/via7-via9 incremental geometric rules.
"""
import os,sys,json,gzip,hashlib
from pathlib import Path
assert os.environ.get('SLURM_JOB_ID'),'Run geometry replay in a compute allocation'
c=json.loads(Path(sys.argv[1]).read_text());sys.path.insert(0,c['rules_dir']);import lower_rules as g
def transform(rect,tr):
 sx,dx,sy,dy=tr;x0,y0,x1,y1=rect
 return tuple((min(sx*x0+dx,sx*x1+dx),min(sy*y0+dy,sy*y1+dy),max(sx*x0+dx,sx*x1+dx),max(sy*y0+dy,sy*y1+dy)))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
ports={}
for line in Path(c['ports_tsv']).read_text().splitlines():
 a=line.split('\t')
 if a[0]=='term':
  assert a[4].startswith('n') and a[4][1:].isdigit()
  ports[c['block']+'.'+a[1]]=int(a[4][1:])
native=[]
with gzip.open(c['native_gz'],'rt') as f:
 for line in f:
  if line.startswith('#'):continue
  name,layer,role,*box=line.rstrip().split('\t')
  if layer not in g.LAYERS:continue
  owner=int(name[1:]) if name.startswith('n') and name[1:].isdigit() and not role.endswith('obs') else -1
  native.append((owner,g.LAYERS[layer],transform(list(map(int,box)),c['native_transform'])))
checker=g.Checker(native);errors=[];count=0;seen=[]
overlay=json.loads(Path(c['overlay_json']).read_text())['by_terminal']
for pin,pieces in sorted(overlay.items()):
 if not pin.startswith(c['block']+'.'):continue
 assert pin in ports,('Missing exact final BTerm',pin)
 seen.append(pin)
 for layer,rect in pieces:
  box=transform(rect,c['overlay_transform']);count+=1
  try:checker.verify(ports[pin],layer,box)
  except AssertionError as e:errors.append(dict(pin=pin,layer=layer,rect=box,error=str(e)))
  checker.add(ports[pin],layer,box)
assert seen,'No overlay endpoints selected'
result=dict(passed=not errors,block=c['block'],checked_shapes=count,checked_terminals=len(seen),errors=errors,config=c,input_sha256={k:sha(c[k]) for k in ['native_gz','ports_tsv','overlay_json']},scope='Fixed lower-overlay versus newly routed native geometry; incremental legacy rules only, not full GDS DRC or connectivity proof')
Path(c['output']).write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k not in ['errors','config']},indent=2));sys.exit(bool(errors))
