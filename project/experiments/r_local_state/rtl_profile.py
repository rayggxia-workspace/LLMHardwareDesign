"""Measure a real unchanged RTL/corpus/parameter ST case before rescheduling."""
from pathlib import Path
import os,subprocess,json,hashlib,time,struct
R=Path.cwd();P=R/'project/experiments/r_local_state';S=P/'experimental_finalize'
B=R.parent;O=R/'rtl-profile';O.mkdir(exist_ok=False)
C=B.parent/'issue-157-r-architecture/attempt003/results/corpus'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
cpus=sorted(os.sched_getaffinity(0));assert len(cpus)==16
source={str(f.relative_to(R)):sha(f)for f in S.glob('*.sv')}
assert source=={n:sha(B/'attempt327/project/rtl/r_local_state'/Path(n).name)for n in source}
old=B/'attempt010/results/1024/init-0.json';baseline=json.loads(old.read_text());assert baseline['passed']
case=baseline['cases'][14];inp=C/case['case'];assert sha(inp)==case['input_sha256']
os.environ['VERILATOR_ROOT']='/public/home/yuzelu/opt/eda/verilator-5.042/share/verilator'
V=Path('/public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator')
cmd=[str(V),'--cc','--exe','--build','-j','16','--threads','1','-Wno-fatal','--top-module','r_stream_local','-GWORDS=1024','-GFINALIZE_PIPELINE=1','-CFLAGS','-O1 -DTEST_WORDS=1024','--Mdir',str(O/'engine'),str(S/'r_state_store.sv'),str(S/'r_stream_local.sv'),str(P/'test_engine.cpp')]
with(O/'build.log').open('w')as log:subprocess.run(['taskset','-c',','.join(map(str,cpus))]+cmd,stdout=log,stderr=subprocess.STDOUT,check=True)
assert sha(P/'test_engine.cpp')==sha(B/'attempt327/project/experiments/r_local_state/test_engine.cpp')
mtlog=B/'attempt327/results/1024/test-0-14.log'
observation=dict(path=str(mtlog),bytes=mtlog.stat().st_size,mtime=mtlog.stat().st_mtime,observed=time.time())
start=time.monotonic()
with(O/'case.log').open('w')as log:subprocess.run(['taskset','-c',str(cpus[0]),str(O/'engine/Vr_stream_local'),str(inp),'+verilator+rand+reset+0','+verilator+seed+166'],stdout=log,stderr=subprocess.STDOUT,check=True)
elapsed=time.monotonic()-start;result=json.loads((O/'case.log').read_text());h=struct.unpack('<8I',inp.read_bytes()[:32]);extra=h[2]*h[3]*2
assert result['passed']and result['cycles']==case['result']['cycles']+extra
assert {k:v for k,v in result.items()if k!='cycles'}=={k:v for k,v in case['result'].items()if k!='cycles'}
observation['bytes_after']=mtlog.stat().st_size;observation['observed_after']=time.time()
if observation['bytes']==observation['bytes_after']==0:observation['ongoing_mt_runtime_lower_bound_seconds']=observation['observed_after']-observation['mtime']
record=dict(passed=True,source_sha256=source,capacity=1024,finalize_pipeline=1,case=14,initialization=0,result=result,seconds=elapsed,st_affinity=[cpus[0]],compile_affinity=cpus,mt_observation=observation,command=cmd,inputs={str(f):sha(f)for f in [V,inp,old,P/'test_engine.cpp',O/'build.log',O/'case.log']},scope='Real same RTL/parameter/case ST numeric measurement; ongoing MT lower bound is an observation, not a completed paired MT benchmark. No physical qualification.')
(O/'receipt.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record))
