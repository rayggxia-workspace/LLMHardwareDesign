import hashlib,json,re
from pathlib import Path
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def require(c,m):
 if not c:raise ValueError(m)
def read_profile(root):
 n=root/'native';r=json.loads((n/'results/result.json').read_bytes());c=json.loads((n/'collection.json').read_bytes())
 require(r['passed'] and r['functional_passed'] and r['default_exact_pairs']==27 and r['area']['status']=='passed','native gates')
 require(sum(len(v['runs']) for v in r['tests'].values())==186,'native coverage')
 for p,v in c['files'].items():require(sha(n/p)==v['sha256'],'native receipt drift '+p)
 for p,v in r['source_sha256'].items():
  if p.startswith('project/rtl/'):require(sha(root/'source'/p)==v,'native RTL drift '+p)
 table=[]
 for depth in [0,2,4]:
  timing=[]
  for name in ['unary_tile','binary_tile']:
   runs=[v for v in r['tests']['s32q'+str(depth)]['runs'] if v['case']==name];require(len(runs)==3,'tile seeds')
   periods=set()
   for v in runs:
    s=(n/'results'/v['summary']).read_text();require(sha(n/'results'/v['summary'])==v['summary_sha256'],'tile log drift')
    m=[{k:int(x) for k,x in re.findall(r'(\w+)=(-?\d+)',l)} for l in s.splitlines() if l.startswith('QUEUE_MEASURE ')]
    require(m==[v['measurements']] and m[0]['commands']==16 and m[0]['writes']==16 and m[0]['ACKs']==16,'tile native accounting')
    require(m[0]['reads']==(16 if name=='unary_tile' else 32),'tile reads');periods.add(m[0]['cycles'])
   require(len(periods)==1,'timing seed drift');timing.append(periods.pop())
  table.append(timing)
 return dict(source_commit=r['source_commit'],result_sha256=sha(n/'results/result.json'),table=table,trace_audit=r['generation']['trace_audit'],
             scope='four-lane S32 staged U tile, full measured S/ACK service; partial tiles charged as full64; shape/contract mapping only',
             full_model_RTL_calibrated=False,actual_model_values_verified=False)
