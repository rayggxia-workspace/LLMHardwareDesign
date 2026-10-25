"""Exact raw mapped GDN checkpoints; no output-register injection or cut wrapper."""
import argparse,hashlib,json,subprocess,time,resource,traceback
from pathlib import Path
import numpy as np
from contracts import CONTRACT
from verify import snapshot,SNAP,check_artifacts
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def put(p,x):Path(p).write_text(json.dumps(x,indent=2,sort_keys=True)+'\n',encoding='utf8',newline='\n')
def bound(p):
 m=json.loads((p/'manifest.json').read_text());check_artifacts(p,m);return m

def main():
 p=argparse.ArgumentParser();p.add_argument('task',choices=['prepare','build','sim']);p.add_argument('--out',type=Path,required=True);p.add_argument('--map',type=Path);p.add_argument('--library',type=Path);p.add_argument('--input',type=Path);p.add_argument('--real',type=Path);p.add_argument('--receipt',type=Path);p.add_argument('--prepared',type=Path);p.add_argument('--build',type=Path);p.add_argument('--case',choices=['first','rescale'],default='first');p.add_argument('--stall',type=int,choices=[0,1],default=0);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False);bd=json.loads((ROOT/'binding.json').read_text());m={'schema':'gdn104-run-v1','status':'ERROR','contract':CONTRACT,'task':a.task,'mode':'checkpoint','implementation':'gate','steps':1,'stall':a.stall,'source':bd}
 for n,h in bd['sources'].items():assert sha(ROOT/n)==h,n
 prefix=['/public/software/singularity-ce-4.3.4/bin/singularity','exec','--bind','/public/home/yuzelu/opt/eda:/eda:ro','--pwd',str(a.out),'/public/home/yuzelu/opt/eda/containers/orfs-26Q1-repacked.sif']
 def cmd(name,args):
  argv=[*prefix,*map(str,args)];start=time.monotonic()
  with(a.out/(name+'.log')).open('w',newline='\n')as f:r=subprocess.run(argv,cwd=a.out,stdout=f,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,timeout=1200,preexec_fn=lambda:resource.setrlimit(resource.RLIMIT_AS,(32<<30,32<<30)))
  put(a.out/(name+'-command.json'),{'argv':argv,'exit':r.returncode,'seconds':time.monotonic()-start,'wall_cap_seconds':1200,'child_AS_cap_bytes':32<<30});assert r.returncode==0,name
 try:
  if a.task=='prepare':
   mm=bound(a.map);im=bound(a.input);rm=bound(a.real);rc=json.loads(a.receipt.read_text());assert rc['schema']=='gdn104-receipt-v1'and rc['status']=='PASS_COMPLETE_INTEGER_RTL_NOT_PPA'and rc['profile']=='portable12'and rc['mode']=='real'and rc['commits']==12 and rc['range_waves']==2 and rc['run_manifest_sha256']==sha(a.real/'manifest.json')and rc['input_manifest_sha256']==sha(a.input/'manifest.json')
   assert mm['status']=='LOGIC_ONLY_MAPPED_NOT_PPA'and mm['library_sha256']==sha(a.library)
   for n,h in bd['sources'].items():
    if n.startswith('project/rtl/'):assert mm['source']['sources'].get(n)==rm['source']['sources'].get(n)==h,n
   rows=[json.loads(x)for x in(a.real/'actual.jsonl').read_text().splitlines()];raw=(a.real/'actual.bin').read_bytes();selection={'first':next(i for i,r in enumerate(rows)if r['op']==1),'rescale':next(i for i,r in enumerate(rows)if r['op']==1 and r['retries']>0)};details={}
   with np.load(a.input/'coefficients.npz',allow_pickle=False)as n:basez={k:n[k].copy()for k in n.files}
   for name,i in selection.items():
    folder=a.out/name;folder.mkdir();before=raw[(i-1)*SNAP:i*SNAP];sn=snapshot(before);image=bytearray((a.input/'image.bin').read_bytes());bank=sn['bank'];image[0xa1080:0xa1090]=before[:16];image[0xa1000+bank*64:0xa1040+bank*64]=before[16:80];image[bank*131072:(bank+1)*131072]=before[80:131152];image[0xa0000+bank*2048:0xa0800+bank*2048]=before[131152:];(folder/'image.bin').write_bytes(image)
    z=dict(basez,state_initial=sn['state'],state_units=np.array(sn['units'],dtype=np.int8),initial_output=sn['y']);np.savez_compressed(folder/'coefficients.npz',**z)
    cm=dict(im,steps=1,position=sn['position'],version=sn['version'],epoch=sn['epoch'],units=sn['units'],bank=bank,profile='portable12-checkpoint-'+name,checkpoint={'source_run_manifest_sha256':sha(a.real/'manifest.json'),'source_row':i-1,'slot':rows[i]['slot'],'snapshot_sha256':hashlib.sha256(before).hexdigest(),'expected_after_sha256':hashlib.sha256(raw[i*SNAP:(i+1)*SNAP]).hexdigest()},initial_output='actual previously accepted published Y')
    cm['artifacts']=[{'path':q.name,'bytes':q.stat().st_size,'sha256':sha(q)}for q in folder.iterdir()if q.is_file()];put(folder/'manifest.json',cm);details[name]={'input_path':str(folder),'input_manifest_sha256':sha(folder/'manifest.json'),'slot':rows[i]['slot'],'retries':rows[i]['retries']}
   script='read_json '+str(a.map/'mapped.json')+'\nwrite_verilog -noattr -noexpr '+str(a.out/'mapped.v')+'\ndesign -reset\nread_liberty -ignore_miss_func -ignore_miss_dir '+str(a.library)+'\nwrite_verilog -noattr '+str(a.out/'cells.v')+'\n';(a.out/'export.ys').write_text(script,newline='\n');cmd('export',['yosys','-s',a.out/'export.ys']);m.update(status='EXACT_RAW_MAP_REAL_CHECKPOINTS',cases=details,map_manifest_sha256=sha(a.map/'manifest.json'),library_sha256=sha(a.library),actual_map_sha256=sha(a.map/'mapped.json'),real_receipt_sha256=sha(a.receipt),pilot={'wall_cap_seconds_per_step':1200,'register_injection':False,'scope':'two actual complete twohead checkpoints; continuous32/12 is RTL only'})
  elif a.task=='build':
   pm=bound(a.prepared);assert pm['status']=='EXACT_RAW_MAP_REAL_CHECKPOINTS';cmd('build',['/eda/verilator-5.042/bin/verilator','--cc','--exe','--build','-j','8','-Wno-fatal','--top-module','gdn104','--prefix','Vgdn104','--Mdir',a.out/'obj','--output-split','15000','--output-split-cfuncs','200','-CFLAGS','-std=c++17 -O2',a.prepared/'mapped.v',a.prepared/'cells.v',ROOT/'project/rtl/norm_service/store82.sv',HERE/'gdn_sim.cpp']);m.update(status='GATE_BUILT_NOT_EXECUTED',binary_sha256=sha(a.out/'obj/Vgdn104'),prepared_manifest_sha256=sha(a.prepared/'manifest.json'))
  else:
   pm=bound(a.prepared);bm=bound(a.build);assert bm['status']=='GATE_BUILT_NOT_EXECUTED'and bm['binary_sha256']==sha(a.build/'obj/Vgdn104')and bm['prepared_manifest_sha256']==sha(a.prepared/'manifest.json')
   for n,h in bd['sources'].items():
    if n.startswith('project/rtl/')or n.endswith('/gdn_sim.cpp'):assert bm['source']['sources'].get(n)==h,n
   case=pm['cases'][a.case];inp=Path(case['input_path']);assert sha(inp/'manifest.json')==case['input_manifest_sha256'];cmd('sim',[a.build/'obj/Vgdn104',inp/'image.bin',a.out,a.stall,1,'checkpoint',case['slot']]);m.update(status='GATE_EXECUTED_NOT_RECEIVED',input_manifest_sha256=sha(inp/'manifest.json'),build_manifest_sha256=sha(a.build/'manifest.json'),prepared_manifest_sha256=sha(a.prepared/'manifest.json'),first_slot=case['slot'],case=a.case)
 except Exception as e:m.update(error=str(e),traceback=traceback.format_exc());raise
 finally:m['artifacts']=[{'path':q.name,'bytes':q.stat().st_size,'sha256':sha(q)}for q in sorted(a.out.iterdir())if q.is_file()and q.name!='manifest.json'];put(a.out/'manifest.json',m)
 print(m['status'])
if __name__=='__main__':main()
