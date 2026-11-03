"""Build the unchanged protocol scoreboard against an identical generated model.

Only reuse model/runtime objects if every generated C++/header byte matches.
Otherwise compile the protocol model normally. Both routes run all three original
protocol initializations and compare the original completed MT protocol results.
This construction/smoke evidence never substitutes for the full192-case gate.
"""
from pathlib import Path
import argparse,json,hashlib,os,subprocess,shutil,shlex

p=argparse.ArgumentParser()
p.add_argument('--profile',type=Path,required=True)
p.add_argument('--reference-queue',type=Path,required=True)
p.add_argument('--in-progress-profile',action='store_true',help='Construct the model pair after completed build and exact three-case smoke checks; never reuse these results for acceptance')
a=p.parse_args()
S=a.profile.resolve();P=S.parent/'project/experiments/r_local_state'
O=Path.cwd()/'protocol-link';O.mkdir(exist_ok=False)
T=O/'protocol'
sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
read=lambda f:json.loads(f.read_text())
binding=read(S/'BUILD_BINDING.json')
if a.in_progress_profile:
 assert binding['simulation_threads']==1
 baseline_arg=binding['inputs'];baseline_paths=[Path(n)if Path(n).is_absolute()else S.parent/n for n in baseline_arg if n.endswith('/results/1024/init-0.json')];assert len(baseline_paths)==1
 baseline=read(baseline_paths[0]);assert baseline['passed']
 smoke=[]
 for n in [0,1,2]:
  f=S/('measurement-'+str(n)+'.json');r=read(f);assert r['case']==n and r['result']['passed']and r['result']==baseline['cases'][n]['result']and r['input_sha256']==baseline['cases'][n]['input_sha256']
  assert r['log_sha256']==sha(S/('case-0-'+str(n)+'.log'));smoke.append(dict(path=str(f),sha256=sha(f)))
 profile=dict(inputs=binding['inputs'],binary_sha256=sha(S/'engine/Vr_stream_local'))
 (O/'CONSTRUCTION_SMOKE.json').write_text(json.dumps(dict(qualification=False,model_build_completed=True,engine_binary_sha256=profile['binary_sha256'],smokes=smoke,scope='Completed exact netlist model build and three original reference checks permit protocol construction only. The unfinished longest diagnostic and all smoke results grant no acceptance; full fresh192 remains mandatory.'),indent=2)+'\n')
else:
 profile=read(S/'receipt.json');assert profile['passed']and profile['capacity']==1024 and profile['simulation_threads']==1
assert not(S/'BUILD_COMPLETE.json').exists() and not(S/'protocol').exists()
profile_inputs={str(Path(name)if Path(name).is_absolute()else S.parent/name):digest for name,digest in profile['inputs'].items()}
for name,digest in profile_inputs.items():assert sha(Path(name))==digest
assert sha(S/'engine/Vr_stream_local')==profile['binary_sha256']
assert (S/'cells.v').is_file()
assert sha(P/'test_protocol.cpp')==sha(Path(__file__).parent/'test_protocol.cpp')
command=list(binding['command']);assert command.count('--build')==1
assert command[command.index('--threads')+1]=='1'
assert command[command.index('--Mdir')+1]==str(S/'engine')
assert str(S/'cells.v')in command and str(P/'test_engine.cpp')in command
makeflags=[]
if '-MAKEFLAGS'in command:
 idx=command.index('-MAKEFLAGS');makeflags=shlex.split(command[idx+1]);del command[idx:idx+2]
assert makeflags==['OPT_FAST=-O1','OPT_SLOW=-O0']
command.remove('--build');command[command.index('--Mdir')+1]=str(T)
command[command.index(str(P/'test_engine.cpp'))]=str(P/'test_protocol.cpp')
cores=sorted(os.sched_getaffinity(0));assert cores
os.environ['VERILATOR_ROOT']='/public/home/yuzelu/opt/eda/verilator-5.042/share/verilator'
runtime=Path(os.environ['VERILATOR_ROOT'])/'include';engine_start=(S/'BUILD_BINDING.json').stat().st_mtime
runtime_files=sorted(f for f in runtime.rglob('*')if f.is_file()and(f.suffix in ['.h','.hpp','.cpp','.inl','.inc']or f.name=='verilated.mk'))
assert runtime_files and all(f.stat().st_ctime<=engine_start for f in runtime_files),'Runtime source changed after engine build began; require a new complete model build'
runtime_binding={str(f):dict(sha256=sha(f),bytes=f.stat().st_size,ctime=f.stat().st_ctime)for f in runtime_files}
(O/'RUNTIME_SOURCE_BINDING.json').write_text(json.dumps(dict(engine_build_binding_mtime=engine_start,files=runtime_binding,scope='Versioned external runtime headers/sources predate engine build and remain byte-identical during protocol construction; compiler/image/options are unchanged.'),indent=2)+'\n')
with(O/'generate.log').open('w')as log:subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,check=True)

def generated(folder):
 return {f.name:sha(f)for f in folder.iterdir()if f.is_file()and f.suffix in ['.cpp','.h']}
engine=generated(S/'engine');protocol=generated(T)
assert 'Vr_stream_local.h'in engine and len(engine)>10
reuse=engine==protocol;objects={}
if reuse:
 lib=S/'engine/Vr_stream_local__ALL.a';assert lib.is_file()
 members=subprocess.check_output(['ar','t',str(lib)],universal_newlines=True).splitlines()
 assert members and all(name.startswith('Vr_stream_local')and name.endswith('.o')for name in members)
 shared=[lib]+sorted((S/'engine').glob('verilated*.o'))
 assert any(f.name=='verilated.o'for f in shared)
 for src in shared:
  dest=T/src.name;assert not dest.exists()
  shutil.copyfile(src,dest);assert sha(src)==sha(dest)
  objects[src.name]=dict(source=str(src),destination=str(dest),sha256=sha(src))
identity=dict(all_generated_source_bytes_identical=reuse,engine_generated=engine,protocol_generated=protocol,shared_objects=objects,scope='Object reuse only for identical model C++/header bytes and the same compiler/image/options. A mismatch requires a fresh ordinary model build; no result reuse.')
(O/'MODEL_SOURCE_IDENTITY.json').write_text(json.dumps(identity,indent=2)+'\n')
make=['make','-C',str(T),'-f','Vr_stream_local.mk','-j',str(len(cores))]+makeflags
for name in objects:make+=['-o',name]
with(O/'build.log').open('w')as log:subprocess.run(make,stdout=log,stderr=subprocess.STDOUT,check=True)
assert generated(S/'engine')==engine and generated(T)==protocol
reference=read(a.reference_queue/'BUILD_BINDING.json')
netlist=Path(reference['netlist']);assert reference['inputs'][str(netlist)]==sha(netlist)=='c7c59ae0560563f317650e729e88bf173b89ca3b5c5c2b7c17508971c8b98ab8'
assert str(netlist)in command
rows=[]
for i in range(3):
 old=a.reference_queue/('protocol-'+str(i)+'.log');oldrow=read(Path(str(old)+'.json'))
 assert oldrow['passed'] and oldrow['case']==-1 and oldrow['initialization']==i and oldrow['log_sha256']==sha(old)
 args=['taskset','-c',str(cores[0]),str(T/'Vr_stream_local'),'+verilator+rand+reset+'+str(i),'+verilator+seed+'+str(166+i)]
 log=O/('protocol-smoke-'+str(i)+'.log')
 with log.open('w')as stream:subprocess.run(args,stdout=stream,stderr=subprocess.STDOUT,check=True)
 result=read(log);assert result['passed'] and result==read(old)==oldrow['result']
 rows.append(dict(initialization=i,result=result,log_sha256=sha(log),reference_log=str(old),reference_log_sha256=sha(old)))
(S/'protocol').mkdir()
for name in ['Vr_stream_local','Vr_stream_local__verFiles.dat']:
 shutil.copy2(T/name,S/'protocol'/name);assert sha(T/name)==sha(S/'protocol'/name)
inputs=dict(profile_inputs)
for name,row in runtime_binding.items():assert sha(Path(name))==row['sha256'];inputs[name]=row['sha256']
for folder in [S/'engine',T,S/'protocol']:
 for f in folder.iterdir():
  if f.is_file()and(f.suffix in ['.cpp','.h']or f.name.endswith('__verFiles.dat')or f.name=='Vr_stream_local'):inputs[str(f)]=sha(f)
for f in ([O/'CONSTRUCTION_SMOKE.json']if a.in_progress_profile else[S/'receipt.json'])+[S/'BUILD_BINDING.json',P/'test_protocol.cpp',Path(__file__).resolve(),O/'MODEL_SOURCE_IDENTITY.json',O/'RUNTIME_SOURCE_BINDING.json',O/'generate.log',O/'build.log',a.reference_queue/'BUILD_BINDING.json']:inputs[str(f)]=sha(f)
for row in rows:
 f=Path(row['reference_log']);inputs[str(f)]=sha(f);inputs[str(f)+'.json']=sha(Path(str(f)+'.json'))
for row in objects.values():
 for key in ['source','destination']:inputs[row[key]]=sha(Path(row[key]))
pair=dict(passed=True,qualification=False,capacity=1024,simulation_threads=1,profile=str(S),protocol_origin=str(T),build_support_attempt=str(Path.cwd()),inputs=inputs,codegen_command=command,make_command=make,identical_model_objects_reused=reuse,protocol_smokes=rows,scope='New exact718 model shared between unchanged engine/protocol C++ harnesses. No functional result reuse; full fresh192 remains mandatory.')
(S/'PAIR_BUILD_BINDING.json').write_text(json.dumps(pair,indent=2)+'\n')
(S/'BUILD_COMPLETE.json').write_text(json.dumps(dict(passed=True,capacity=1024,simulation_threads=1,inputs=inputs,binaries={kind:sha(S/kind/'Vr_stream_local')for kind in ['engine','protocol']},pair_binding_sha256=sha(S/'PAIR_BUILD_BINDING.json')),indent=2)+'\n')
