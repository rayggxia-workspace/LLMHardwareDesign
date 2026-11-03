from pathlib import Path
import subprocess,json,os,hashlib,concurrent.futures as cf,itertools,time
R=Path.cwd();P=R/'work/YUZE-LU/162/r256-integration-20261103';O=R/'results';O.mkdir(exist_ok=False)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
inputs=json.loads((R/'INPUTS.json').read_text())
for n,h in inputs.items():assert sha(R/n)==h,n
assert sha(R/'project/rtl/r_local_state/r_stream_local.sv')=='dc41d52eb88efe6cc592683b788d09da980c1c01e779ab54db9fb647d730363d'
assert sha(R/'project/rtl/r_local_state/r_state_store.sv')=='7b50c3abae20587ac49726fed375da6390fc1d4a260ae299939fc6725dae1d40'
V='/public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator'
os.environ['VERILATOR_ROOT']='/public/home/yuzelu/opt/eda/verilator-5.042/share/verilator'
assert len(os.sched_getaffinity(0))==24
def call(cmd,log,env=None):
 with log.open('w')as f:return subprocess.run(list(map(str,cmd)),stdout=f,stderr=subprocess.STDOUT,env=env).returncode
core=R/'project/rtl/control_v1';exp=R/'project/experiments/control_v1'
sources=list(sorted(core.glob('*.sv')))
sources+=[R/'project/rtl/block_feed_v1'/(n+'.sv')for n in ('block_feed_s_macro','block_feed_s16k','block_feed_loader')]
sources+=[R/'project/rtl/block_v2'/(n+'.sv')for n in ('block_v2_m','block_v2_n','block_v2_n_group','block_v2_e','block_v2_g')]
sources+=[R/'project/rtl/block_v1/transaction6k.sv',exp/'BUF_X16.v',R/'project/rtl/r_local_state/r_stream_local.sv',R/'project/rtl/r_local_state/r_state_store.sv']
includes=['-I'+str(R/'project/rtl/block_v2'),exp/'native_t_lint.vlt',exp/'native_r_lint.vlt']
models={'system':('control_system',sources,exp/'test_system.cpp',includes,[],''),'adapter_r':('control_adapter_r',[core/'control_adapter_r.sv'],exp/'test_adapter_r.cpp',[],[],'')}
for name,top,test,parameter,define in [
 ('route8','control_route','test_route.cpp','ENDPOINTS=8','TEST_ENDPOINTS=8'),
 ('arbiter7','control_s_arbiter','test_s_arbiter.cpp','CLIENTS=7','TEST_CLIENTS=7'),
 ('reset28','control_reset_distribution','test_reset.cpp','BRANCHES=28','TEST_RESET_BRANCHES=28'),
 ('status8','control_status','test_status.cpp','QUEUES=8','TEST_QUEUES=8'),
 ('route7','control_route','test_route.cpp','',''),
 ('arbiter6','control_s_arbiter','test_s_arbiter.cpp','',''),
 ('c7','control_c','test_c.cpp','',''),
 ('reset25','control_reset_distribution','test_reset.cpp','',''),
 ('status7','control_status','test_status.cpp','','')]:
 src=[core/(top+'.sv')]+([exp/'BUF_X16.v']if top=='control_reset_distribution'else[])
 models[name]=(top,src,exp/test,[],['-G'+parameter]if parameter else[],'-D'+define if define else'')
def build(name):
 top,src,cpp,inc,parameters,defines=models[name];out=O/name;out.mkdir()
 common=[V,'--top-module',top,*parameters,*inc,*src]
 rc=call([*common,'--lint-only','-Wall'],out/'lint.log')
 if rc:raise RuntimeError('strict lint failed '+name)
 rc=call([*common,'--cc','--exe','--build','-j','12','--threads','1','--Mdir',out/'obj','--x-initial','unique','--x-assign','unique','-CFLAGS','-std=c++17 -O1 '+defines,cpp],out/'build.log')
 if rc:raise RuntimeError('build failed '+name)
 return name,out/'obj'/('V'+top)
started=time.time()
baseline=call([V,'--lint-only','-Wall','-Wno-fatal','--top-module','r_stream_local',R/'project/rtl/r_local_state/r_stream_local.sv',R/'project/rtl/r_local_state/r_state_store.sv'],O/'frozen-r-raw-lint.log')
assert baseline==0,'Frozen R has a fatal lint error'
with cf.ThreadPoolExecutor(max_workers=2)as pool:binaries=dict(pool.map(build,models))
def test(t):
 name,init,seed=t;out=O/name;log=out/f'i{init}-s{seed}.log';env=dict(os.environ,CONTROL_TEST_SEED=str(seed))
 rc=call([binaries[name],'+verilator+rand+reset+'+str(init),'+verilator+seed+'+str(seed)],log,env)
 rec={'model':name,'initialization':init,'seed':seed,'exit_code':rc,'log_sha256':sha(log),'passed':False}
 if rc==0:rec['result']=json.loads(log.read_text());rec['passed']=rec['result']['passed']
 return rec
with cf.ThreadPoolExecutor(max_workers=24)as pool:rows=list(pool.map(test,itertools.product(models,range(3),[162,163,164])))
for n,h in inputs.items():assert sha(R/n)==h,n
receipt={'rtl_integration_passed':all(x['passed']for x in rows),'cases':rows,'input_sha256':inputs,'frozen_r256_unchanged':True,
 'binaries':{n:sha(p)for n,p in binaries.items()},'affinity':sorted(os.sched_getaffinity(0)),'workers':24,'elapsed_seconds':time.time()-started,
 'physical_system_qualified':False,'scope':'Actual behavioral RTL: C/D, eight queues, R adapter, seven S clients and seven compute/storage macros. Original three programs plus five R programs and six rejection cases. Component test uses explicitly modeled S/R peers.'}
(O/'RECEIPT.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({k:v for k,v in receipt.items()if k not in ('cases','input_sha256')}))
assert receipt['rtl_integration_passed'],'RTL integration test failure'
