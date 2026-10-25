"""Proof of original Yosys next-state cone with arbitrary current RTL register state."""
import argparse,copy,hashlib,json,subprocess,time,traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def put(p,x):Path(p).write_text(json.dumps(x,indent=2)+'\n')
def extract(data):
 t=data['modules']['chain85'];cells=t['cells'];nets=t['netnames']
 leaves={n:nets[n]['bits']for n in('epoch','state','pending','reset','soft_abort','cmd','cfg','ext_valid','ext_response_epoch','link_take')}
 stop={b for bs in leaves.values()for b in bs if isinstance(b,int)};drivers={}
 for n,c in cells.items():
  for port,direction in c['port_directions'].items():
   if direction=='output':
    for bit in c['connections'][port]:
     if isinstance(bit,int):
      if bit in drivers:raise ValueError('multiple drivers')
      drivers[bit]=n
 regs=[(n,c)for n,c in cells.items()if c['type']=='$dff'and c['connections']['Q']==nets['epoch']['bits']]
 if len(regs)!=1:raise ValueError('one actual32bit epoch DFF expected')
 regname,reg=regs[0]
 if int(reg['parameters']['WIDTH'],2)!=32:raise ValueError('full epoch width')
 outputs={'epoch_next':reg['connections']['D'],'cmd_ready_actual':nets['cmd_ready']['bits'],'cmd_accept_actual':nets['cmd_accept']['bits'],'ext_take_actual':nets['ext_take']['bits'],'link_valid_actual':cells['link']['connections']['t_valid']}
 chosen=set();active=set()
 def walk(b):
  if not isinstance(b,int)or b in stop:return
  if b not in drivers:raise ValueError('unbound cone leaf '+str(b))
  n=drivers[b]
  if n in chosen:return
  if n in active:raise ValueError('combinational loop')
  c=cells[n]
  if not c['type'].startswith('$')or 'dff'in c['type']or'latch'in c['type']:raise ValueError('unexpected state/peripheral in cone '+n)
  active.add(n)
  for port,direction in c['port_directions'].items():
   if direction=='input':
    for z in c['connections'][port]:walk(z)
  active.remove(n);chosen.add(n)
 for bs in outputs.values():
  for b in bs:walk(b)
 ports={n:{'direction':'input','bits':bs}for n,bs in leaves.items()};ports.update({n:{'direction':'output','bits':bs}for n,bs in outputs.items()})
 result={'creator':'Issue92 exact original combinational cells, registerQ abstracted','modules':{'epoch_cone':{'attributes':{},'ports':ports,'cells':{n:copy.deepcopy(cells[n])for n in sorted(chosen)},'netnames':{n:{'hide_name':0,'bits':p['bits'],'attributes':{}}for n,p in ports.items()}}}}
 return result,{'epoch_register':regname,'epoch_register_cell':reg,'leaf_wires':leaves,'outputs':outputs,'retained_original_cells':sorted(chosen),'state_abstraction':'Arbitrary actual current epoch/state/pending Q and memory_link take; all next-state combinational cells unchanged. No reachability or liveness claim.'}
def monitor():
 return r'''module epoch_check(input wire [31:0] epoch,ext_response_epoch,input wire [2:0] state,input wire pending,reset,soft_abort,cmd,cfg,ext_valid,link_take,output wire proof_ok,output wire [8:0] properties,output wire [31:0] epoch_next,output wire cmd_ready_actual,cmd_accept_actual,ext_take_actual,link_valid_actual);
 epoch_cone d(.epoch(epoch),.ext_response_epoch(ext_response_epoch),.state(state),.pending(pending),.reset(reset),.soft_abort(soft_abort),.cmd(cmd),.cfg(cfg),.ext_valid(ext_valid),.link_take(link_take),.epoch_next(epoch_next),.cmd_ready_actual(cmd_ready_actual),.cmd_accept_actual(cmd_accept_actual),.ext_take_actual(ext_take_actual),.link_valid_actual(link_valid_actual));
 assign properties[0]=reset||(epoch!=32'hffffffff)||(epoch_next==32'hffffffff);
 assign properties[1]=(epoch!=32'hffffffff)||(!cmd_ready_actual&&!cmd_accept_actual);
 assign properties[2]=!reset||((epoch_next==0)&&!cmd_ready_actual&&!cmd_accept_actual);
 assign properties[3]=reset||(epoch==32'hffffffff)||!(soft_abort||cmd_accept_actual)||(epoch_next==epoch+32'd1);
 assign properties[4]=reset||soft_abort||cmd_accept_actual||(epoch_next==epoch);
 assign properties[5]=reset||(epoch!=32'hffffffff)||!(soft_abort||state==0)||(ext_take_actual&&!link_valid_actual);
 assign properties[6]=(ext_response_epoch==epoch)||(ext_take_actual&&!link_valid_actual);
 assign properties[7]=reset||(epoch!=32'hffffffff)||soft_abort||(state==0)||(ext_response_epoch!=epoch)||((ext_take_actual==link_take)&&(link_valid_actual==ext_valid));
 assign properties[8]=reset||soft_abort||(state!=0)||pending||cfg||(epoch==32'hffffffff)||(cmd_ready_actual&&(cmd_accept_actual==cmd));
 assign proof_ok=&properties;
endmodule
'''
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--baseline',action='store_true');a=p.parse_args();a.out.mkdir(exist_ok=False);bd=json.loads((ROOT/'binding.json').read_text());m={'status':'ERROR','source':bd,'baseline':a.baseline}
 for n,h in bd['sources'].items():
  if sha(ROOT/n)!=h:raise ValueError('source SHA')
 prefix=['/public/software/singularity-ce-4.3.4/bin/singularity','exec','--bind','/public/home/yuzelu/opt/eda:/eda:ro','--pwd',str(a.out),'/public/home/yuzelu/opt/eda/containers/orfs-26Q1-repacked.sif']
 def run(tag,args):
  argv=[*prefix,*map(str,args)];start=time.monotonic()
  with(a.out/(tag+'.log')).open('w')as f:r=subprocess.run(argv,stdout=f,stderr=subprocess.STDOUT,timeout=180,stdin=subprocess.DEVNULL)
  put(a.out/(tag+'-command.json'),{'argv':argv,'exit':r.returncode,'seconds':time.monotonic()-start});return r.returncode
 try:
  rtl=ROOT/'project/rtl/runtime_cache';sv=[rtl/n for n in('sfu84.sv','mul84.sv','norm84.sv','mfront85.sv')]+[HERE/'baseline-chain85.sv'if a.baseline else rtl/'chain85.sv',ROOT/'project/rtl/norm_service/store82.sv',ROOT/'project/rtl/wide_service/memory_link.sv'];script='read_verilog -sv '+' '.join(map(str,sv))+'\nhierarchy -top chain85\nproc\nopt_expr\nopt_clean\nwrite_json '+str(a.out/'original-proc.json')+'\n';(a.out/'proc.ys').write_text(script)
  if run('proc',['yosys','-s',a.out/'proc.ys']):raise ValueError('original proc failed')
  data=json.loads((a.out/'original-proc.json').read_text());cone,bind=extract(data);put(a.out/'cone.json',cone);put(a.out/'extraction.json',dict(bind,original_json_sha256=sha(a.out/'original-proc.json')));(a.out/'monitor.v').write_text(monitor())
  script='read_json '+str(a.out/'cone.json')+'\nread_verilog '+str(a.out/'monitor.v')+'\nprep -top epoch_check\nflatten\nopt_clean\nsat -verify -prove proof_ok 1 -show-inputs -show-outputs '+('-set ext_valid 1 -set state 0 -set link_take 0 -set reset 0 'if a.baseline else'')+'-dump_json '+str(a.out/'counterexample.json')+'\n';(a.out/'proof.ys').write_text(script);code=run('sat',['yosys','-s',a.out/'proof.ys']);text=(a.out/'sat.log').read_text()
  if a.baseline:
   if code==0 or 'proof did fail'not in text.lower()or not(a.out/'counterexample.json').exists():raise ValueError('original actual cone must expose terminal counterexample')
   m['status']='EXPECTED_ORIGINAL_NEXTSTATE_COUNTEREXAMPLE'
  else:
   if code or 'SUCCESS'not in text:raise ValueError('SAT proof failed')
   m['status']='PASS_ACTUAL_NEXTSTATE_CONE_UNIVERSAL_SAFETY'
  m.update(proof_properties=9,combinational_cells=len(cone['modules']['epoch_cone']['cells']),extraction_sha256=sha(a.out/'extraction.json'))
 except Exception as e:m['error']=str(e);m['traceback']=traceback.format_exc();raise
 finally:m['artifacts']=[{'path':q.name,'bytes':q.stat().st_size,'sha256':sha(q)}for q in a.out.iterdir()if q.is_file()and q.name!='manifest.json'];put(a.out/'manifest.json',m)
 print(m['status'])
if __name__=='__main__':main()
