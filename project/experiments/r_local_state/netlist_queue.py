"""Refill six independent 16-core slots per case, using an immutable cell build."""
from pathlib import Path
import argparse,subprocess,json,hashlib,os,queue,concurrent.futures,struct,time,re
p=argparse.ArgumentParser();p.add_argument('--source-test',type=Path,required=True);p.add_argument('--netlist',type=Path,required=True);p.add_argument('--capacity',type=int,required=True);p.add_argument('--case-parallelism',type=int,choices=range(1,97),default=6);p.add_argument('--reuse-queue',type=Path);p.add_argument('--wait-inflight',action='store_true');p.add_argument('--fresh',action='store_true');a=p.parse_args()
assert not a.fresh or not(a.reuse_queue or a.wait_inflight)
P=Path(__file__).resolve().parent
S=a.source_test;O=Path.cwd()/'netlist-queue';O.mkdir(exist_ok=False);C=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-157-r-architecture/attempt003/results/corpus');M=json.loads((C/'MANIFEST.json').read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();inputs={str(a.netlist):sha(a.netlist),str(S/'cells.v'):sha(S/'cells.v')};cpus=sorted(os.sched_getaffinity(0));assert len(cpus)>=a.case_parallelism and len(cpus)%a.case_parallelism==0
width=len(cpus)//a.case_parallelism
support=[]
if a.fresh:
 complete=json.loads((S/'BUILD_COMPLETE.json').read_text());pair=json.loads((S/'PAIR_BUILD_BINDING.json').read_text())
 assert complete['passed']and pair['passed']and complete['capacity']==pair['capacity']==a.capacity and complete['simulation_threads']==pair['simulation_threads']==1
 assert complete['inputs']==pair['inputs']and complete['pair_binding_sha256']==sha(S/'PAIR_BUILD_BINDING.json')
 for name,digest in complete['inputs'].items():assert sha(Path(name))==digest;inputs[name]=digest
 for f in [S/'BUILD_COMPLETE.json',S/'PAIR_BUILD_BINDING.json',Path(__file__).resolve()]:inputs[str(f)]=sha(f)
 assert len(M['cases'])==63
 for d,role in [(Path.cwd(),'fresh-case-runner'),(S.parent,'exact-model-engine-build'),(Path(pair['build_support_attempt']),'exact-protocol-build'),(S.parents[1]/'attempt672','unchanged-cell-model-origin')]:
  assert d.parent==Path.cwd().parent
  support.append(dict(attempt=str(d),role=role,run_sbatch_sha256=sha(d/'run.sbatch'),files_sha256=sha(d/'FILES.sha256')))
slots=queue.Queue();[slots.put(cpus[i*width:(i+1)*width])for i in range(a.case_parallelism)]
inflight={f.name for f in a.reuse_queue.glob('case-*.log')if f.stat().st_size==0}if a.reuse_queue and a.wait_inflight else set()
for k in ['engine','protocol']:
 b=S/k/'Vr_stream_local';v=S/k/'Vr_stream_local__verFiles.dat';assert b.is_file() and str(a.netlist)in v.read_text() and str(S/'cells.v')in v.read_text();mt=re.search(r'--threads\s+(\d+)',v.read_text());threads=int(mt[1])if mt else 1;assert threads<=width,'simulation threads exceed each allocated affinity slice';inputs[str(b)]=sha(b);inputs[str(v)]=sha(v)
 if a.fresh:
  assert sha(b)==complete['binaries'][k]and threads==1
  cpp=set(re.findall(r'(/[^\s"\']+/test_'+k+r'\.cpp)',v.read_text()));assert len(cpp)==1
  original=Path(next(iter(cpp)));current=P/('test_'+k+'.cpp');assert sha(original)==sha(current)
  for f in [original,current]:inputs[str(f)]=sha(f)
(O/'BUILD_BINDING.json').write_text(json.dumps({'inputs':inputs,'source_test':str(S),'source_checked_job_script_sha256':sha(S.parent/'run.sbatch'),'source_checked_files_sha256':sha(S.parent/'FILES.sha256'),'no_results_reused':a.fresh,'allocated_affinity':cpus,'case_parallelism':a.case_parallelism,'cores_per_slot':width,'worker_sources':support},indent=2)+'\n')
if a.reuse_queue:
 previous=json.loads((a.reuse_queue/'BUILD_BINDING.json').read_text())
 assert previous['inputs'][str(a.netlist)]==sha(a.netlist),'Cannot reuse cases from a different netlist'
 previous_test=Path(previous['source_test'])
 assert sha(previous_test/'cells.v')==sha(S/'cells.v'),'Different cell models'
 for kind in ['engine','protocol']:
  command=(previous_test/kind/'Vr_stream_local__verFiles.dat').read_text()
  cpp=set(re.findall(r'(/[^\s"\']+/test_'+kind+r'\.cpp)',command))
  assert len(cpp)==1 and sha(Path(next(iter(cpp))))==sha(Path(__file__).parent/('test_'+kind+'.cpp')),'Different independent scoreboard'
def task(item):
 i,n=item;kind='protocol'if n<0 else'engine';name=f'protocol-{i}.log'if n<0 else f'case-{i}-{n}.log';old=(a.reuse_queue/name)if a.reuse_queue and (a.reuse_queue/name).exists()else S/name;dest=O/name;rec={'passed':False,'initialization':i,'case':n}
 try:
  if n>=0:
   inp=C/M['cases'][n]['path'];assert sha(inp)==M['cases'][n]['sha256'];rec['corpus']=M['cases'][n]
  if name in inflight:
   while old.stat().st_size==0:time.sleep(5)
   # The writer closes stdout at exit; retry a partially flushed final JSON.
   for _ in range(120):
    try:json.loads(old.read_text());break
    except ValueError:time.sleep(1)
  reused=False
  if not a.fresh and old.is_file():
   try:
    data=old.read_bytes();j=json.loads(data);assert j['passed']is True
    if n>=0:assert j['words']==a.capacity
    dest.write_bytes(data);reused=True;rec['reused_from']=str(old)
   except (ValueError,AssertionError,KeyError):pass
  if not reused:
   cc=slots.get()
   try:
    rec.update(affinity_cpus=cc,node=os.environ.get('SLURMD_NODENAME'),slurm_job_id=os.environ.get('SLURM_JOB_ID'),slurm_step_id=os.environ.get('SLURM_STEP_ID'))
    cmd=['taskset','-c',','.join(map(str,cc)),str(S/kind/'Vr_stream_local')]+([str(inp)]if n>=0 else[])+['+verilator+rand+reset+'+str(i),'+verilator+seed+'+str(166+i)]
    with dest.open('w')as f:subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,check=True)
   finally:slots.put(cc)
   j=json.loads(dest.read_text());assert j['passed']is True
  if n>=0:assert j['words']==a.capacity
  rec.update(passed=True,result=j,log_sha256=sha(dest))
 except Exception as e:rec['error']=repr(e)
 (O/(name+'.json')).write_text(json.dumps(rec,indent=2)+'\n');return rec
items=[(i,-1)for i in range(3)]+[(i,n)for i in range(3)for n in range(len(M['cases']))]
assert len(items)==192 and set(items)=={(i,n)for i in range(3)for n in range(-1,63)}
def cost(x):
 if x[1]<0:return 10**18
 h=struct.unpack('<8I',(C/M['cases'][x[1]]['path']).read_bytes()[:32]);return h[1]*h[2]*h[3]
items.sort(key=cost,reverse=True)
with concurrent.futures.ThreadPoolExecutor(max_workers=a.case_parallelism)as pool:rows=list(pool.map(task,items))
assert inputs=={f:sha(Path(f))for f in inputs}
if a.fresh:assert all('reused_from'not in r and(not r['passed']or len(r.get('affinity_cpus',[]))==width)for r in rows)
(O/'receipt.json').write_text(json.dumps({'passed':all(r['passed']for r in rows),'capacity':a.capacity,'inputs':inputs,'tasks':rows,'slots':a.case_parallelism,'cores_per_slot':width,'worker_sources':support,'no_results_reused':a.fresh,'actual_nodes':sorted({r['node']for r in rows if r.get('node')}),'resource_reason':str(a.case_parallelism)+' independent dynamically refilled cases within '+str(len(cpus))+' allocated CPUs; actual model threads checked against each disjoint affinity slice.','scope':'All original192 numeric/protocol cases execute freshly; no profile/smoke/old result reused.'if a.fresh else'Exact immutable cell-build independent numeric/protocol case queue; each completed source log reused with byte SHA, no pending or incomplete case accepted.'},indent=2)+'\n');assert all(r['passed']for r in rows)
