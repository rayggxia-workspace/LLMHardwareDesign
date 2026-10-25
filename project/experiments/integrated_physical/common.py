"""Issue98 server-only provenance/tool wrappers; no credentials or scheduler policy."""
import hashlib,json,os,resource,subprocess,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
EDA=Path('/public/home/yuzelu/opt/eda');D=EDA/'cache/bazel-repacked/0472cb7817e9c4d6e974e10cde266a63/external/bazel-orfs++orfs_repositories+docker_orfs';F=D/'OpenROAD-flow-scripts/flow';P=F/'platforms/nangate45';OR=D/'OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad';STA=OR.with_name('sta');LIB=P/'lib/NangateOpenCellLibrary_typical.lib';TECH=P/'lef/NangateOpenCellLibrary.tech.lef';LEF=P/'lef/NangateOpenCellLibrary.macro.mod.lef'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def put(p,x):Path(p).write_text(json.dumps(x,ensure_ascii=False,indent=2,sort_keys=True)+'\n',encoding='utf-8')
def need(v,s):
 if not v:raise ValueError(s)
def sources():
 b=load(ROOT/'binding.json')
 need(type(b['commit'])is str and len(b['commit'])==40,'exact source commit')
 for n,h in b['sources'].items():need(sha(ROOT/n)==h,'source SHA '+n)
 return b

def artifacts(folder):
 folder=Path(folder);m=load(folder/'manifest.json');seen=set()
 need(type(m.get('artifacts'))is list and len(m['artifacts'])>0,'artifact inventory')
 for e in m['artifacts']:
  q=folder/e['path'];need(q.parent==folder and q.is_file()and e['path']not in seen,'direct unique artifact');seen.add(e['path'])
  need(type(e['bytes'])is int and q.stat().st_size==e['bytes']and sha(q)==e['sha256'],'artifact bytes/SHA')
 return m

def manifest(out,m):
 m['artifacts']=[{'path':q.name,'bytes':q.stat().st_size,'sha256':sha(q)}for q in sorted(out.iterdir())if q.is_file()and q.name!='manifest.json'];put(out/'manifest.json',m)

def command(out,name,args,seconds=900,eda=True):
 args=list(map(str,args))
 if args[0]in(str(OR),str(STA)):args=[str(D/'lib64/ld-linux-x86-64.so.2'),'--library-path',str(D/'usr/lib/x86_64-linux-gnu'),*args]
 if eda:args=['/public/software/singularity-ce-4.3.4/bin/singularity','exec','--bind',str(EDA)+':/eda:ro','--pwd',str(out),str(EDA/'containers/orfs-26Q1-repacked.sif'),*args]
 start=time.monotonic();r=None;err=None
 try:
  with(out/(name+'.log')).open('w')as f:r=subprocess.run(args,cwd=out,stdout=f,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,timeout=seconds)
 except Exception as e:err=repr(e);raise
 finally:put(out/(name+'-command.json'),{'argv':args,'exit':None if r is None else r.returncode,'seconds':time.monotonic()-start,'timeout_seconds':seconds,'error':err})
 need(r.returncode==0,'command failed '+name)

def resource_snapshot():
 cpus=int(os.environ.get('SLURM_CPUS_PER_TASK','0'));need(cpus==8,'eight actual allocated CPUs')
 return {'slurm_job':os.environ.get('SLURM_JOB_ID'),'cpus_per_task':cpus,'affinity_cpu_ids':sorted(os.sched_getaffinity(0)),'threads':8,'meminfo':Path('/proc/meminfo').read_text(),'cgroup':Path('/proc/self/cgroup').read_text(),'rlimit_as':list(resource.getrlimit(resource.RLIMIT_AS)),'scheduler_memory':'CPU-only allocation: cluster RealMemory=1MB is not physical RAM; no --mem request. DefMem/MaxMem UNLIMITED; not a scheduler-enforced private RAM reservation.'}

def tcl_script(lines):return 'if {[catch {\n'+'\n'.join(lines)+'\n} msg opts]} {puts stderr $msg; puts stderr [dict get $opts -errorinfo]; exit 1}\nexit 0\n'
