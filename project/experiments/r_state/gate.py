"""Actual raw mapped gate checkpoint qualification; bounded 20 minute single-step pilot."""
import argparse,hashlib,json,subprocess,time,traceback,struct,resource
from pathlib import Path
from contracts import CONTRACT
from reference import step
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def put(p,x):Path(p).write_text(json.dumps(x,indent=2,sort_keys=True)+'\n',newline='\n')
def need(v,s):
 if not v:raise ValueError(s)
def bound(folder):
 m=json.loads((folder/'manifest.json').read_text())
 for e in m['artifacts']:need((folder/e['path']).stat().st_size==e['bytes']and sha(folder/e['path'])==e['sha256'],'artifact '+e['path'])
 return m
def main():
 p=argparse.ArgumentParser();p.add_argument('task',choices=['prepare','build','sim','receive','pilot']);p.add_argument('--out',type=Path,required=True);p.add_argument('--map',type=Path);p.add_argument('--library',type=Path);p.add_argument('--input',type=Path);p.add_argument('--real',type=Path);p.add_argument('--receipt',type=Path);p.add_argument('--prepared',type=Path);p.add_argument('--build',type=Path);p.add_argument('--implementation',choices=['rtl','gate'],default='gate');p.add_argument('--case',choices=['first','rescale'],default='first');p.add_argument('--stall',type=int,choices=[0,1],default=0);p.add_argument('--runs',nargs='*',type=Path);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False);bd=json.loads((ROOT/'binding.json').read_text());m={'schema':'r99-gate-v1','status':'ERROR','source':bd,'task':a.task,'implementation':a.implementation,'case':a.case,'stall':a.stall,'contract':CONTRACT}
 for n,h in bd['sources'].items():need(sha(ROOT/n)==h,'source '+n)
 prefix=['/public/software/singularity-ce-4.3.4/bin/singularity','exec','--bind','/public/home/yuzelu/opt/eda:/eda:ro','--pwd',str(a.out),'/public/home/yuzelu/opt/eda/containers/orfs-26Q1-repacked.sif']
 def cmd(name,args,timeout=1200):
  argv=[*prefix,*map(str,args)];start=time.monotonic()
  with(a.out/(name+'.log')).open('w',newline='\n')as f:r=subprocess.run(argv,cwd=a.out,stdout=f,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,text=True,timeout=timeout,preexec_fn=lambda:resource.setrlimit(resource.RLIMIT_AS,(32<<30,32<<30)))
  put(a.out/(name+'-command.json'),{'argv':argv,'exit':r.returncode,'seconds':time.monotonic()-start,'wall_cap_seconds':timeout,'child_address_space_cap_bytes':32<<30})
  need(r.returncode==0,'failed '+name)
 try:
  if a.task=='prepare':
   mm=bound(a.map);im=bound(a.input);rm=bound(a.real);receipt=json.loads(a.receipt.read_text());need(receipt['status']=='PASS_FULL_HEAD_RTL_BIGINT'and receipt['mode']=='real'and receipt['committed_steps']==72 and receipt['run_manifest_sha256']==sha(a.real/'manifest.json')and receipt['input_manifest_sha256']==sha(a.input/'manifest.json'),'strict72 L2 binding');need(mm['status']=='LOGIC_ONLY_MAPPED_NOT_PPA'and mm['library_sha256']==sha(a.library),'actualmap')
   for n,h in bd['sources'].items():
    if n.startswith('project/rtl/'):need(mm['source']['sources'].get(n)==h and rm['source']['sources'].get(n)==h,'exact RTL-map-execution source')
   rows=[json.loads(x)for x in(a.real/'actual.jsonl').read_text().splitlines()];raw=(a.real/'actual.bin').read_bytes();re=[i for i,x in enumerate(rows)if x['op']==1 and x['retries']>0];need(re,'real range event required');selection={'first':next(i for i,x in enumerate(rows)if x['op']==1),'rescale':re[0]};details={}
   base=(a.input/'head0.bin').read_bytes()
   for name,i in selection.items():
    before=raw[(i-1)*131600:i*131600];after=raw[i*131600:(i+1)*131600];desc=before[:16];word=int.from_bytes(desc,'little');bank=(word>>112)&1;pos=(word>>32)&0xffffffff;image=bytearray(base);image[bank*131072:(bank+1)*131072]=before[16:131088];image[0xa0000+bank*512:0xa0000+(bank+1)*512]=before[131088:];image[0xa0400:0xa0410]=desc;(a.out/(name+'.bin')).write_bytes(image);(a.out/(name+'-expected.bin')).write_bytes(after);details[name]={'source_row':i,'position_before':pos,'original_retries':rows[i]['retries'],'source_before_sha256':hashlib.sha256(before).hexdigest(),'source_after_sha256':hashlib.sha256(after).hexdigest(),'initial_image_sha256':sha(a.out/(name+'.bin'))}
   script='read_json '+str(a.map/'mapped.json')+'\nwrite_verilog -noattr -noexpr '+str(a.out/'mapped.v')+'\ndesign -reset\nread_liberty -ignore_miss_func -ignore_miss_dir '+str(a.library)+'\nwrite_verilog -noattr '+str(a.out/'cells.v')+'\n';(a.out/'export.ys').write_text(script,newline='\n');cmd('export',['yosys','-s',a.out/'export.ys']);m.update(status='EXACT_RAW_MAP_REAL_CHECKPOINTS',cases=details,map_manifest_sha256=sha(a.map/'manifest.json'),library_sha256=sha(a.library),real_receipt_sha256=sha(a.receipt),actual_map_sha256=sha(a.map/'mapped.json'),pilot={'single_step_wall_cap_seconds':1200,'checkpoint_domain':'two actual steps only; 72 continuous remains RTL evidence','register_injection':False,'no_retry_on_timeout_without_recorded_review':True})
  elif a.task=='build':
   pm=bound(a.prepared);need(pm['status']=='EXACT_RAW_MAP_REAL_CHECKPOINTS','prepared rawgate');sv=[a.prepared/'mapped.v',a.prepared/'cells.v',ROOT/'project/rtl/norm_service/store82.sv']if a.implementation=='gate'else[ROOT/'project/rtl/r_state/r99.sv',ROOT/'project/rtl/runtime_cache/mul84.sv',ROOT/'project/rtl/norm_service/store82.sv',ROOT/'project/rtl/wide_service/memory_link.sv'];cmd('build',['/eda/verilator-5.042/bin/verilator','--cc','--exe','--build','-j','8','-Wno-fatal','--top-module','r99','--prefix','Vr99','--Mdir',a.out/'obj','--output-split','15000','--output-split-cfuncs','200','-CFLAGS','-std=c++17 -O2',*sv,HERE/'checkpoint_sim.cpp']);m.update(status='CHECKPOINT_BUILT_NOT_EXECUTED',binary_sha256=sha(a.out/'obj/Vr99'),prepared_manifest_sha256=sha(a.prepared/'manifest.json'))
  elif a.task=='sim':
   pm=bound(a.prepared);bm=bound(a.build);need(bm['status']=='CHECKPOINT_BUILT_NOT_EXECUTED'and bm['implementation']==a.implementation and bm['prepared_manifest_sha256']==sha(a.prepared/'manifest.json')and bm['binary_sha256']==sha(a.build/'obj/Vr99'),'binary/prepared binding');
   for n,h in bd['sources'].items():
    if n.startswith('project/rtl/')or n.endswith(('/r_sim.cpp','/checkpoint_sim.cpp')):need(bm['source']['sources'].get(n)==h,'checkpoint binary source')
   cmd('simulation',[a.build/'obj/Vr99',a.prepared/(a.case+'.bin'),a.out,a.stall,0]);m.update(status='CHECKPOINT_EXECUTED_NOT_RECEIVED',build_path=str(a.build),prepared_path=str(a.prepared),prepared_manifest_sha256=sha(a.prepared/'manifest.json'),build_manifest_sha256=sha(a.build/'manifest.json'))
  else:
   pm=bound(a.prepared);need(pm['status']=='EXACT_RAW_MAP_REAL_CHECKPOINTS','exactmap prep');results=[];seen=set()
   for run in a.runs:
    rm=bound(run);need(rm['status']=='CHECKPOINT_EXECUTED_NOT_RECEIVED'and rm['prepared_manifest_sha256']==sha(a.prepared/'manifest.json'),'checkpointrun');bm=bound(Path(rm['build_path']));need(sha(Path(rm['build_path'])/'manifest.json')==rm['build_manifest_sha256']and bm['implementation']==rm['implementation']and bm['binary_sha256']==sha(Path(rm['build_path'])/'obj/Vr99'),'actual gate or RTL build binary');name=rm['case'];key=(rm['implementation'],name,rm['stall']);need(key not in seen,'duplicate checkpoint');seen.add(key);
    for n,h in bd['sources'].items():
     if n.startswith('project/rtl/')or n.endswith(('/r_sim.cpp','/checkpoint_sim.cpp')):need(rm['source']['sources'].get(n)==h and bm['source']['sources'].get(n)==h,'checkpoint execution source')
    rows=[json.loads(x)for x in(run/'actual.jsonl').read_text().splitlines()];raw=(run/'actual.bin').read_bytes();need(len(rows)==2 and len(raw)==263200,'full checkpoint snapshots');image=(a.prepared/(name+'.bin')).read_bytes();desc=image[0xa0400:0xa0410];w=int.from_bytes(desc,'little');pos=(w>>32)&0xffffffff;ep=(w>>64)&0xffffffff;u=(w>>96)&65535;u=u-65536 if u>=32768 else u;bank=(w>>112)&1;state=list(struct.unpack_from('<32768i',image,bank*131072));y=list(struct.unpack_from('<128i',image,0xa0000+bank*512));before=desc+struct.pack('<32768i',*state)+struct.pack('<128i',*y);need(raw[:131600]==before,'actual restored full checkpoint');dt,alpha,skip,_=struct.unpack_from('<iIiI',image,0xb0010+pos*2592);v=struct.unpack_from('<640i',image,0xb0020+pos*2592);state,y,unit,epoch,retry=step(state,u,ep,v[:128],v[128:384],v[384:],dt,alpha,skip);newdesc=(0x52393901|((pos+1)<<32)|(epoch<<64)|((unit&65535)<<96)|((1-bank)<<112)|(1<<118)|(1<<119)).to_bytes(16,'little');after=newdesc+struct.pack('<32768i',*state)+struct.pack('<128i',*y);need(raw[131600:]==after and after==(a.prepared/(name+'-expected.bin')).read_bytes(),'complete independent and actual continuousRTL checkpoint equality');need(rows[1]['status']==0 and rows[1]['retries']==retry,'actual checkpoint retry');need(rows[1]['beats']==5*rows[1]['transactions'],'checkpoint bridge');results.append({'implementation':key[0],'case':name,'stall':key[2],'run_manifest_sha256':sha(run/'manifest.json'),'cycles':rows[1]['cycles'],'retries':retry,'position':pos,'all_state_codes_compared':65536,'all_readout_codes_compared':256,'actual_sha256':sha(run/'actual.bin')})
   required={('gate','first',0)}if a.task=='pilot'else{(k,n,s)for k in ['rtl','gate']for n in ['first','rescale']for s in [0,1]};need(seen==required,'exact checkpoint coverage');m.update(status='PASS_RAW_GATE_FIRST_STEP_PILOT'if a.task=='pilot'else'PASS_RAW_MAPPED_GATE_TWO_REAL_CHECKPOINTS',results=results,pilot=pm['pilot'])
 except Exception as e:m.update(error=str(e),traceback=traceback.format_exc());raise
 finally:m['artifacts']=[{'path':q.name,'bytes':q.stat().st_size,'sha256':sha(q)}for q in sorted(a.out.iterdir())if q.is_file()and q.name!='manifest.json'];put(a.out/'manifest.json',m)
 print(m['status'])
if __name__=='__main__':main()
