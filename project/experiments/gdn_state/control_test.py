import argparse,json,subprocess,time
from pathlib import Path
from inputs import sha,put
ROOT=Path(__file__).resolve().parents[3];P=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False);bd=json.loads((ROOT/'binding.json').read_text())
for n,h in bd['sources'].items():assert sha(ROOT/n)==h
prefix=['/public/software/singularity-ce-4.3.4/bin/singularity','exec','--bind','/public/home/yuzelu/opt/eda:/eda:ro','--pwd',str(a.out),'/public/home/yuzelu/opt/eda/containers/orfs-26Q1-repacked.sif'];commands=[]
for tag,args in [('build',['/eda/verilator-5.042/bin/verilator','--cc','--exe','--build','-j','2','-Wno-fatal','--top-module','gdn104','--prefix','Vgdn104','--Mdir',a.out/'obj','-CFLAGS','-std=c++17 -O2',ROOT/'project/rtl/gdn_state/gdn104.sv',ROOT/'project/rtl/gdn_state/wide104.sv',ROOT/'project/rtl/runtime_cache/mul84.sv',ROOT/'project/rtl/norm_service/store82.sv',ROOT/'project/rtl/wide_service/memory_link.sv',P/'control_sim.cpp']),('run',[a.out/'obj/Vgdn104',a.input/'image.bin',a.out])]:
 argv=[*prefix,*map(str,args)];start=time.monotonic();r=subprocess.run(argv,cwd=a.out,capture_output=True,text=True,timeout=1200);(a.out/(tag+'.log')).write_text(r.stdout+r.stderr,encoding='utf8',newline='\n');commands.append({'argv':argv,'exit':r.returncode,'seconds':time.monotonic()-start});assert r.returncode==0,tag
rows=[json.loads(x)for x in(a.out/'control.jsonl').read_text().splitlines()];assert len(rows)==13
for i,row in enumerate(rows[:12]):assert row=={'case':i,'restore_status':9,'step_status':4,'external_unchanged':True}
assert rows[12]=={'case':12,'kind':'generation_terminal_RTL_output_register_injection','injected':4294967294,'observed':4294967295,'rejected_cycles':11,'stale_drained':1}
put(a.out/'receipt.json',{'schema':'gdn104-control-v1','status':'PASS_INVALID_RESTORE_AND_TRANSPORT_TERMINAL','source':bd,'input_manifest_sha256':sha(a.input/'manifest.json'),'cases':rows,'commands':commands,'actual_sha256':sha(a.out/'actual.bin'),'rows_sha256':sha(a.out/'actual.jsonl'),'control_sha256':sha(a.out/'control.jsonl'),'limits':['terminal uses RTL register injection; not raw gate proof','invalid metadata is rejected; no authenticity claimed']});print('PASS_CONTROL',len(rows))
