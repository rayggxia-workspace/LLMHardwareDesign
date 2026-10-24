"""Issue68 immutable input intake: checks bytes, prior formats and source contracts only."""
import argparse,hashlib,json,os,platform,zipfile
from pathlib import Path
import numpy as np

def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb')as f:
  for b in iter(lambda:f.read(8<<20),b''):h.update(b)
 return h.hexdigest()

def load(p):return json.loads(Path(p).read_text())

def main():
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--binding',type=Path,required=True);a=p.parse_args()
 if a.out.exists():raise ValueError('new output required')
 b=load(a.binding)
 if sha(__file__)!=b['intake_sha256']:raise ValueError('source binding')
 found={};records=[]
 for name in ['state01','state02','long-state01','long-state02','norm03','norm04']:
  folder=a.root/name;m=load(folder/'manifest.json')
  if m['status']!='PASS':raise ValueError('old execution '+name)
  for fn,meta in m['artifacts'].items():
   q=(folder/fn).resolve()
   if not q.is_relative_to(folder.resolve()):raise ValueError('artifact escape')
   if q.stat().st_size!=meta['bytes']or sha(q)!=meta['sha256']:raise ValueError('artifact '+str(q))
  found[name]=m
  records.append({'folder':str(folder),'manifest_sha256':sha(folder/'manifest.json'),'artifacts':m['artifacts']})
 for first,second in [('state01','state02'),('long-state01','long-state02'),('norm03','norm04')]:
  if found[first]['artifacts']!=found[second]['artifacts']:raise ValueError('round mismatch '+first)
 old=load(a.root/'long-state01/state-results.json');native=load(a.root/'state01/state-results.json');norm=load(a.root/'norm03/norm.json')
 if len(old)!=48 or sum(r['integer_steps']==256 for r in old)!=24 or sum(r['integer_steps']==1 for r in old)!=24:raise ValueError('long scope')
 failures=[]
 for row in old:
  if row['id'].startswith(('layer0-end2048.','layer0-end8192.')):
   sat=row['execution']['saturations'];expected=184 if row['id'].startswith('layer0-end2048.')else193
   if sat!=expected:raise ValueError('preserved saturation '+row['id'])
   failures.append({'id':row['id'],'state_saturations':sat,'quality_accepted':row['quality_accepted']})
 header={}
 for name,fn in [('state01','evaluation.S32.D31.npz'),('long-state01','layer0-end8192.S32.D31.npz')]:
  with np.load(a.root/name/fn,allow_pickle=False)as z:
   q,k,v=z['q'],z['k'],z['v'];initial=z['state_initial'];units=z['state_units']
   if q.shape[-2:]!=(2,128)or initial.shape!=(2,128,128):raise ValueError('actual recurrent group shape')
   header[name]={'query_shape':list(q.shape),'value_shape':list(v.shape),'initial_shape':list(initial.shape),'state_units':units.tolist(),'state_trace_stored_dtype':str(z['state_trace'].dtype)}
 for row in norm:
  if row['status']!='PASS'or row['hidden']!=2560:raise ValueError('norm scope')
  c=row['candidate_cost']
  if c['aligned_I64_row_bytes']!=20480 or c['finite_buffer_alternatives']['two_source_passes']['sum_and_units_read_bytes_per_row']!=51200:raise ValueError('finite buffer source contract')
  if c['aligned_I64_row_fits_V16KiB']:raise ValueError('false free buffer')
 a.out.mkdir(parents=True)
 result={'status':'PASS_INTAKE_ONLY','source_binding':b,'source_root':str(a.root),'records':records,'long_conditions':len(old),'long256_conditions':24,'long1_conditions':24,'native_conditions':len(native),'norm_conditions':len(norm),'preserved_range_failures':failures,'actual_group_shapes':header,'environment':{'python':platform.python_version(),'numpy':np.__version__,'slurm':{k:os.environ.get(k)for k in ['SLURM_JOB_ID','SLURM_CPUS_PER_TASK','SLURMD_NODENAME']}},'not_accepted':['new range protocol','new service schedule','application quality','target hardware/PPA']}
 (a.out/'intake.json').write_text(json.dumps(result,indent=2)+'\n',newline='\n')
 print(json.dumps({'status':result['status'],'source_folders':len(records),'source_artifacts':sum(len(x['artifacts'])for x in records)}),flush=True)
if __name__=='__main__':main()
