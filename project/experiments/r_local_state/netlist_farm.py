"""Immutable final-cell cases as dynamically replenished16-core Slurm tasks.

The existing C++ scoreboards,192 cases and final receipt gates are unchanged.
An array concurrency cap36 permits six96-core nodes' worth of independent work;
Slurm places tasks within the task's eight eligible nodes as slots become free.
"""
from pathlib import Path
import argparse,hashlib,json,os,re,shutil,struct,subprocess

p=argparse.ArgumentParser();p.add_argument('--stage',choices=['prepare','worker','collect','smoke'],required=True)
p.add_argument('--source-test',type=Path);p.add_argument('--netlist',type=Path);p.add_argument('--capacity',type=int,choices=[256,1024]);p.add_argument('--queue',type=Path);p.add_argument('--worker-attempt',type=Path);p.add_argument('--baseline',type=Path);a=p.parse_args()
P=Path(__file__).resolve().parent
C=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-157-r-architecture/attempt003/results/corpus')
sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
read=lambda f:json.loads(f.read_text())

if a.stage=='prepare':
 assert a.source_test and a.netlist and a.capacity and a.worker_attempt
 S=a.source_test;O=Path.cwd()/'netlist-queue';O.mkdir(exist_ok=False)
 complete=read(S/'BUILD_COMPLETE.json');assert complete['passed']and complete['simulation_threads']==16
 inputs={str(f):sha(f)for f in [a.netlist,S/'cells.v',C/'MANIFEST.json']}
 for path,digest in complete['inputs'].items():assert sha(Path(path))==digest;inputs[path]=digest
 for kind in ['engine','protocol']:
  binary=S/kind/'Vr_stream_local';vf=S/kind/'Vr_stream_local__verFiles.dat';text=vf.read_text()
  assert str(a.netlist)in text and str(S/'cells.v')in text
  assert int(re.search(r'--threads\s+(\d+)',text)[1])==16
  cpp=set(re.findall(r'(/[^\s"\']+/test_'+kind+r'\.cpp)',text));assert len(cpp)==1
  original=Path(next(iter(cpp)));assert sha(original)==sha(P/('test_'+kind+'.cpp'))
  assert sha(binary)==complete['binaries'][kind]
  for f in [binary,vf,original]:inputs[str(f)]=sha(f)
 M=read(C/'MANIFEST.json');assert len(M['cases'])==63
 items=[dict(initialization=i,case=n)for i in range(3)for n in range(-1,63)]
 def cost(item):
  if item['case']<0:return 10**18
  h=struct.unpack('<8I',(C/M['cases'][item['case']]['path']).read_bytes()[:32]);return h[1]*h[2]*h[3]
 items.sort(key=cost,reverse=True)
 for idx,item in enumerate(items):item['task_id']=idx
 sources=[]
 for d in [Path.cwd(),a.worker_attempt]:
  assert d.parent==Path.cwd().parent
  sources.append(dict(attempt=str(d),run_sbatch_sha256=sha(d/'run.sbatch'),files_sha256=sha(d/'FILES.sha256')))
 binding=dict(inputs=inputs,source_test=str(S),capacity=a.capacity,netlist=str(a.netlist),cases=M['cases'],items=items,worker_sources=sources,farm_runner_sha256=sha(Path(__file__)),source_checked_job_script_sha256=sha(S.parent/'run.sbatch'),source_checked_files_sha256=sha(S.parent/'FILES.sha256'),scope='Exact same192 independent cases; Slurm array tasks each16cores, concurrency cap36, eligible nodes fixed in submitted scripts')
 (O/'BUILD_BINDING.json').write_text(json.dumps(binding,indent=2)+'\n')
 raise SystemExit(0)

assert a.queue and a.queue.is_absolute()
B=read(a.queue/'BUILD_BINDING.json');assert B['farm_runner_sha256']==sha(Path(__file__))
for path,digest in B['inputs'].items():assert sha(Path(path))==digest
for row in B['worker_sources']:
 d=Path(row['attempt']);assert sha(d/'run.sbatch')==row['run_sbatch_sha256']and sha(d/'FILES.sha256')==row['files_sha256']
S=Path(B['source_test'])

if a.stage=='worker':
 idx=int(os.environ['SLURM_ARRAY_TASK_ID']);item=B['items'][idx];assert item['task_id']==idx
 i,n=item['initialization'],item['case'];kind='protocol'if n<0 else'engine';name=f'protocol-{i}.log'if n<0 else f'case-{i}-{n}.log'
 dest=a.queue/name;record=a.queue/(name+'.json');assert not dest.exists()and not record.exists()
 cpus=sorted(os.sched_getaffinity(0));assert len(cpus)==16 and int(os.environ['SLURM_CPUS_PER_TASK'])==16,'Worker must have an exact16CPU Slurm binding'
 rec=dict(passed=False,initialization=i,case=n,task_id=idx,slurm_job_id=os.environ['SLURM_JOB_ID'],array_job_id=os.environ['SLURM_ARRAY_JOB_ID'],node=os.environ['SLURMD_NODENAME'],affinity_cpus=cpus)
 try:
  cmd=['taskset','-c',','.join(map(str,cpus)),str(S/kind/'Vr_stream_local')]
  if n>=0:
   case=B['cases'][n];inp=C/case['path'];assert sha(inp)==case['sha256'];rec['corpus']=case;cmd.append(str(inp))
  cmd+=['+verilator+rand+reset+'+str(i),'+verilator+seed+'+str(166+i)]
  with dest.open('w')as f:subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,check=True)
  result=read(dest);assert result['passed']is True
  if n>=0:assert result['words']==B['capacity']
  rec.update(passed=True,result=result,log_sha256=sha(dest))
 except Exception as e:rec['error']=repr(e)
 record.write_text(json.dumps(rec,indent=2)+'\n');raise SystemExit(0 if rec['passed']else 1)

def receive(item):
 i,n=item['initialization'],item['case'];name=f'protocol-{i}.log'if n<0 else f'case-{i}-{n}.log'
 row=read(a.queue/(name+'.json'));assert row['task_id']==item['task_id']and row['initialization']==i and row['case']==n
 assert row['passed']is True and len(row['affinity_cpus'])==16 and row['log_sha256']==sha(a.queue/name)
 assert row['result']==read(a.queue/name)and row['result']['passed']is True
 if n>=0:
  assert row['corpus']==B['cases'][n]and sha(C/row['corpus']['path'])==row['corpus']['sha256']and row['result']['words']==B['capacity']
 return row

if a.stage=='smoke':
 assert a.baseline;old=read(a.baseline/'receipt.json');assert old['passed']and old['capacity']==B['capacity']
 assert old['inputs'][B['netlist']]==B['inputs'][B['netlist']]
 previous={(r['initialization'],r['case']):r for r in old['tasks']};ids=[0,1,2,189,190,191];rows=[]
 for idx in ids:
  row=receive(B['items'][idx]);assert row['result']==previous[(row['initialization'],row['case'])]['result'];rows.append(row)
 (Path.cwd()/'FARM_SMOKE_RECEIPT.json').write_text(json.dumps(dict(passed=True,baseline=str(a.baseline),baseline_receipt_sha256=sha(a.baseline/'receipt.json'),tested_ids=ids,tasks=rows,scope='Six actual exact111 cell cases equal existing119 results; wrapper validation only, not192case receipt or macro qualification'),indent=2)+'\n')
 raise SystemExit(0)

assert a.stage=='collect'
O=Path.cwd()/'netlist-queue';assert not O.exists();rows=[];errors=[]
for item in B['items']:
 try:rows.append(receive(item))
 except Exception as e:errors.append(dict(item=item,error=repr(e)))
assert len(B['items'])==192 and {(r['initialization'],r['case'])for r in B['items']}=={(i,n)for i in range(3)for n in range(-1,63)}
for path,digest in B['inputs'].items():assert sha(Path(path))==digest
shutil.copytree(a.queue,O)
result=dict(passed=not errors and len(rows)==192,capacity=B['capacity'],inputs=B['inputs'],tasks=rows,errors=errors,worker_sources=B['worker_sources'],slots=36,cores_per_slot=16,actual_nodes=sorted({r['node']for r in rows}),resource_reason='Slurm array tasks each16CPU; dynamic admission cap36, six tasks per96CPU node, within eight allowed nodes. No batch waits or case changes.',scope='Exact same immutable final-cell192-case numeric/protocol reception; no missing, failed or pending case accepted.')
(O/'receipt.json').write_text(json.dumps(result,indent=2)+'\n');assert result['passed'],errors
