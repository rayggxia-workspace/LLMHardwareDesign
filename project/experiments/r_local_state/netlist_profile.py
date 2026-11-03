"""Measure unchanged exact final-cell numeric cases with a one-thread model.

This diagnostic has no macro-qualification authority. It neither changes nor
cancels the original running192-case array. Compilation uses its actual allocated
CPU fragment; simulation uses one CPU, with the original C++ scoreboard/corpus.
"""
from pathlib import Path
import argparse,os,json,hashlib,subprocess,time

p=argparse.ArgumentParser()
p.add_argument('--physical',type=Path,required=True)
p.add_argument('--source-build',type=Path,required=True)
p.add_argument('--baseline',type=Path,required=True)
a=p.parse_args()
P=Path(__file__).resolve().parent;O=Path.cwd()/'netlist-profile';O.mkdir(exist_ok=False)
sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
read=lambda f:json.loads(f.read_text())
cores=sorted(os.sched_getaffinity(0));assert cores and len(cores)==int(os.environ['SLURM_CPUS_PER_TASK'])
V=Path('/public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator')
L=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib')
C=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-157-r-architecture/attempt003/results/corpus')
net=a.physical/'flow/results/nangate45/r166_1024/base/6_final.v'
build=read(a.source_build/'BUILD_COMPLETE.json');assert build['passed']
assert read(a.physical/'receipt.json')['exit']==0
assert sha(net)=='c7c59ae0560563f317650e729e88bf173b89ca3b5c5c2b7c17508971c8b98ab8'
assert sha(L)=='8d540a4d4cf6d09d27c87ad067857a9c0c2eeb023ab7a56e058cd3113db4e9b1'
for name,digest in build['inputs'].items():assert sha(Path(name))==digest
cpp=[Path(n)for n in build['inputs']if Path(n).name=='test_engine.cpp'];assert len(cpp)==1 and sha(cpp[0])==sha(P/'test_engine.cpp')
models=a.source_build/'cells.v'
assert str(models)in(a.source_build/'engine/Vr_stream_local__verFiles.dat').read_text()
baseline=read(a.baseline);assert baseline['passed']
cases=read(C/'MANIFEST.json')['cases'];assert len(cases)==len(baseline['cases'])==63
inputs={str(f):sha(f)for f in [net,L,models,V,P/'test_engine.cpp',a.baseline,a.source_build/'BUILD_COMPLETE.json',C/'MANIFEST.json',Path(__file__)]}
os.environ['VERILATOR_ROOT']='/public/home/yuzelu/opt/eda/verilator-5.042/share/verilator'
command=[str(V),'--cc','--exe','--build','-j',str(len(cores)),'--threads','1','--x-initial','unique','--x-assign','unique','-Wno-fatal','--top-module','r_stream_local','--output-split','12000','--output-split-cfuncs','150','-CFLAGS','-O1 -DTEST_WORDS=1024','--Mdir',str(O/'engine'),str(net),str(models),str(P/'test_engine.cpp')]
(O/'BUILD_BINDING.json').write_text(json.dumps(dict(inputs=inputs,command=command,compile_affinity=cores,simulation_threads=1,qualification=False),indent=2)+'\n')
start=time.monotonic()
with(O/'build.log').open('w')as log:subprocess.run(['taskset','-c',','.join(map(str,cores))]+command,stdout=log,stderr=subprocess.STDOUT,check=True)
build_seconds=time.monotonic()-start
rows=[]
for n in [0,1,2,35]:
 case=cases[n];inp=C/case['path'];old=baseline['cases'][n]
 assert sha(inp)==case['sha256']==old['input_sha256']
 cmd=['taskset','-c',str(cores[0]),str(O/'engine/Vr_stream_local'),str(inp),'+verilator+rand+reset+0','+verilator+seed+166']
 start=time.monotonic();log=O/('case-0-'+str(n)+'.log')
 with log.open('w')as stream:subprocess.run(cmd,stdout=stream,stderr=subprocess.STDOUT,check=True)
 elapsed=time.monotonic()-start;result=read(log)
 assert result['passed'] and result==old['result'],(n,result,old['result'])
 rows.append(dict(case=n,input_sha256=sha(inp),result=result,seconds=elapsed,command=cmd,log_sha256=sha(log)))
 (O/('measurement-'+str(n)+'.json')).write_text(json.dumps(rows[-1],indent=2)+'\n')
assert all(sha(Path(n))==digest for n,digest in inputs.items())
(O/'receipt.json').write_text(json.dumps(dict(passed=True,qualification=False,capacity=1024,simulation_threads=1,simulation_affinity=[cores[0]],compile_affinity=cores,build_seconds=build_seconds,inputs=inputs,binary_sha256=sha(O/'engine/Vr_stream_local'),cases=rows,scope='Four unchanged final-cell numeric cases match original independent RTL scoreboard results exactly, including cycle counts. Runtime diagnostic only; no missing192-case or physical gate replaced.'),indent=2)+'\n')
