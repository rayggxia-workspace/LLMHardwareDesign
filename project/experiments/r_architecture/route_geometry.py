"""Read-only DEF/SPEF analysis; distinguish extracted wire C from Liberty pin C.
DEF centerline totals are checked against the router report before interpretation.
"""
from pathlib import Path
import json,re,hashlib,collections,os,subprocess,concurrent.futures,argparse
B=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-157-r-architecture')
P=Path(__file__).resolve().parent;O=Path.cwd()/'results';O.mkdir(exist_ok=False)
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
 return h.hexdigest()
def analyze(candidate,attempt):
 trial=B/(f'attempt{attempt:03d}' if isinstance(attempt,int) else attempt)/'physical/flow'
 root=trial/'results/nangate45'/('rarch157_'+candidate)/'base';d=O/candidate;d.mkdir()
 stages=[]
 for s in ['3_3_place_gp','5_1_grt','5_2_route','6_final']:
  odb=root/(s+'.odb')
  if not odb.exists():continue
  before=sha(odb);env=os.environ.copy();env.update(INPUT_ODB=str(odb),OUTPUT_TSV=str(d/(s+'.tsv')))
  with(d/(s+'.log')).open('w')as f:r=subprocess.run(['openroad','-exit',str(P/'odb_probe.tcl')],env=env,stdout=f,stderr=subprocess.STDOUT)
  assert sha(odb)==before;stages.append(dict(stage=s,exit=r.returncode,odb=str(odb),sha256=before))
 selected=set()
 for p in d.glob('*.tsv'):
  for line in p.open():
   parts=line.rstrip().split('\t')
   if parts[0]=='NET':selected.add(parts[1])
 result=dict(candidate=candidate,stages=stages,selected_nets=sorted(selected))
 df=root/'6_final.def';sp=root/'6_final.spef'
 if df.exists():
  before=sha(df);total=collections.Counter();nets={};body=[];inside=False;dbu=None;unsupported=[]
  def consume(lines):
   text=' '.join(lines);name=re.match(r'\s*-\s+(\S+)',text)[1];layers=collections.Counter()
   chunks=re.split(r'\+\s+(?:ROUTED|FIXED|COVER)\s+|\bNEW\s+',text)[1:]
   for chunk in chunks:
    layer=chunk.split()[0];prev=None
    if 'RECT'in chunk:unsupported.append(name)
    for x,y in re.findall(r'\(\s*(\*|-?\d+)\s+(\*|-?\d+)(?:\s+-?\d+)?\s*\)',chunk):
     if prev is None and'*'in[x,y]:raise ValueError(('undefined DEF star',name))
     point=(prev[0]if x=='*'else int(x),prev[1]if y=='*'else int(y))
     if prev is not None:layers[layer]+=(abs(point[0]-prev[0])+abs(point[1]-prev[1]))/dbu
     prev=point
   total.update(layers)
   if name in selected:nets[name]=dict(layers)
  with df.open()as f:
   for line in f:
    if line.startswith('UNITS DISTANCE MICRONS'):dbu=int(line.split()[3])
    if line.startswith('NETS '):inside=True;continue
    if line.startswith('END NETS'):break
    if not inside:continue
    body.append(line)
    if ';'in line:consume(body);body=[]
  assert sha(df)==before
  log=trial/'logs/nangate45'/('rarch157_'+candidate)/'base/5_2_route.log'
  expected={k:float(v)for k,v in re.findall(r'Total wire length on LAYER (\w+) = ([\d.]+) um',log.read_text())}if log.exists()else{}
  delta={k:total[k]-v for k,v in expected.items()};matched=bool(expected)and all(abs(v)<2 for v in delta.values())and not unsupported
  result.update(def_path=str(df),def_sha256=before,def_centerline_um_by_layer=dict(total),router_report_um_by_layer=expected,def_minus_router_um_by_layer=delta,centerline_matches_router_within_2um_each_layer=matched,selected_def_centerline_um_by_layer=nets,rect_paths_not_supported=sorted(set(unsupported)))
 if sp.exists():
  before=sha(sp);ids={};caps={};capunit='';pinpolicy=''
  with sp.open()as f:
   for line in f:
    if line.startswith('*C_UNIT'):capunit=line.strip()
    if line.startswith('*DESIGN_FLOW'):pinpolicy=line.strip()
    m=re.match(r'^(\*\d+) (\S+)\s*$',line)
    if m and m[2]in selected:ids[m[1]]=m[2]
    if line.startswith('*D_NET '):
     _,net,c=line.split()[:3]
     if net in ids:caps[ids[net]]=float(c)
  assert sha(sp)==before
  result.update(spef_path=str(sp),spef_sha256=before,spef_capacitance_unit=capunit,spef_pin_cap_policy=pinpolicy,selected_spef_D_NET_capacitance=caps)
 (d/'GEOMETRY.json').write_text(json.dumps(result,indent=2)+'\n');return result
parser=argparse.ArgumentParser()
parser.add_argument('--trial',action='append',help='Candidate=attempt-relative-path; immutable source flow')
a=parser.parse_args()
trials=[('B256',20),('A0',40),('A1',44)]
if a.trial:
 trials=[]
 for spec in a.trial:
  candidate,relative=spec.split('=',1)
  assert re.fullmatch(r'[A-Za-z0-9]+',candidate)
  assert re.fullmatch(r'attempt[0-9]+(?:/B[0-9]+)?',relative)
  trials.append((candidate,relative))
with concurrent.futures.ThreadPoolExecutor(max_workers=min(3,len(trials)))as pool:rows=list(pool.map(lambda x:analyze(*x),trials))
(O/'GEOMETRY.json').write_text(json.dumps(rows,indent=2)+'\n')
