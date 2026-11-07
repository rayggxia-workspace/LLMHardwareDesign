"""Execute real-bank and inferred-RAM PM protocol checks on the server."""
import argparse,json,hashlib,subprocess,re
from pathlib import Path
H=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def call(cmd,path):
 with path.open('wb') as f:subprocess.run(list(map(str,cmd)),stdout=f,stderr=subprocess.STDOUT,check=True)
def main():
 p=argparse.ArgumentParser();p.add_argument('--stage',type=Path,required=True);p.add_argument('--bank',type=Path,required=True)
 p.add_argument('--verilator',required=True);p.add_argument('--yosys',required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--jobs',type=int,default=4)
 a=p.parse_args();o=a.out.resolve();o.mkdir(parents=True,exist_ok=True)
 assert sha(a.bank)=='6c1c1ca9d183ab7c4c74df056c9730cf352d165301546126e29b644a45ef9de7'
 storage=a.stage/'staged/native/block_feed_s16k_sram.sv';results=[]
 bank_stub=o/'bank.v';bank_stub.write_text(a.bank.read_text().split('  reg [DATA_WIDTH-1:0]    mem',1)[0]+'endmodule\n')
 for backend in (0,1):
  d=o/f'backend-{backend}';d.mkdir(exist_ok=True)
  call([a.verilator,'--binary','--timing','--assert','--timescale-override','1ns/1ps','--x-initial','unique','--x-assign','unique','-Wno-fatal','--top-module','tb_control_pm',f'-GUSE_SRAM={backend}','-j',a.jobs,'--Mdir',d/'obj',H/'control_pm.sv',H/'tb_control_pm.sv',storage,a.bank],d/'compile.log')
  for init,seed in ((1,143),(2,143),(2,144)):
   log=d/f'init-{init}-seed-{seed}.log'
   call([d/'obj/Vtb_control_pm',f'+verilator+rand+reset+{init}',f'+verilator+seed+{seed}'],log)
   assert f'PASS control-pm backend={backend}' in log.read_text()
   results.append({'backend':backend,'init':init,'seed':seed,'passed':True,'log_sha256':sha(log)})
  script=d/'check.ys'
  script.write_text('read_verilog -lib '+json.dumps(str(bank_stub))+'\nread_verilog -sv '+json.dumps(str(storage))+' '+json.dumps(str(H/'control_pm.sv'))+f'\nchparam -set USE_SRAM {backend} control_pm\nhierarchy -check -top control_pm\nproc\nopt\nmemory_dff\nmemory_collect\ncheck -assert\nwrite_json '+json.dumps(str(d/'design.json'))+'\n')
  call([a.yosys,'-s',script],d/'synth.log')
  design=json.loads((d/'design.json').read_text())
  if backend==0:assert any(c['type']=='$mem_v2' for m in design['modules'].values() for c in m.get('cells',{}).values()),'RAM was not inferred'
  else:assert any(c['type']=='s_sram_256x128_freepdk45' for m in design['modules'].values() for c in m.get('cells',{}).values()),'SRAM bank missing'
 d={'schema':'control-pm-validation/1','cases':results,'functional_passed':len(results),'structure_passed':2,'class_count_each':6,'source_sha256':{str(x):sha(x) for x in (H/'control_pm.sv',H/'tb_control_pm.sv',storage,a.bank)},'scope':'Functional models and synthesis structure; no new mapped timing or physical qualification.'}
 d['artifacts_sha256']={str(x.relative_to(o)):sha(x) for x in o.rglob('*') if x.is_file() and not any(y.startswith('obj') for y in x.parts)}
 (o/'report.json').write_text(json.dumps(d,indent=2)+'\n');print('PASS PM functional 6/6 and structure 2/2')
if __name__=='__main__':main()
