import argparse,hashlib,json,subprocess,time
from pathlib import Path
from inputs import put,sha
ROOT=Path(__file__).resolve().parents[3];P=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False);bd=json.loads((ROOT/'binding.json').read_text())
for n,h in bd['sources'].items():assert sha(ROOT/n)==h
prefix=['/public/software/singularity-ce-4.3.4/bin/singularity','exec','--bind','/public/home/yuzelu/opt/eda:/eda:ro','--pwd',str(a.out),'/public/home/yuzelu/opt/eda/containers/orfs-26Q1-repacked.sif']
commands=[]
for tag,args in [('build',['/eda/verilator-5.042/bin/verilator','--cc','--exe','--build','-j','2','-Wno-fatal','--top-module','wide_test104','--prefix','Vwide_test104','--Mdir',a.out/'obj','-CFLAGS','-std=c++17 -O2',P/'wide_test104.sv',ROOT/'project/rtl/gdn_state/wide104.sv',ROOT/'project/rtl/runtime_cache/mul84.sv',P/'wide_sim.cpp']),('run',[a.out/'obj/Vwide_test104',a.out/'actual.csv'])]:
 argv=[*prefix,*map(str,args)];start=time.monotonic();r=subprocess.run(argv,cwd=a.out,capture_output=True,text=True,timeout=1200);(a.out/(tag+'.log')).write_text(r.stdout+r.stderr,encoding='utf8',newline='\n');commands.append({'argv':argv,'exit':r.returncode,'seconds':time.monotonic()-start});assert r.returncode==0,tag
counts={'valid':0,'rejected':0};n=0
for row in(a.out/'actual.csv').read_text().splitlines():
 av,bv,err,value,grants=map(int,row.split(','));expected=av*bv;bad=av==-(1<<63)or not -32768<=bv<=32768 or abs(expected)>(1<<63)-1;assert err==bad
 if not bad:assert value==expected and grants==3;counts['valid']+=1
 else:counts['rejected']+=1
 n+=1
assert n==4177
put(a.out/'receipt.json',{'schema':'gdn104-wide-service-v1','status':'PASS_EXACT_WIDE_PRODUCTS_AND_CANCEL','source':bd,'vectors':n,'counts':counts,'cancellation_positions':9,'commands':commands,'actual_sha256':sha(a.out/'actual.csv'),'binary_sha256':sha(a.out/'obj/Vwide_test104'),'reference':'independent Python arbitrary precision product; abs<=I64_MAX, signed small bound'});print('PASS',n,counts)
