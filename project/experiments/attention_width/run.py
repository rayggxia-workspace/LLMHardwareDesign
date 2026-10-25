"""Server-only variants; unchanged 102/106 drivers and consumers, exact source adapters."""
import argparse,hashlib,json,subprocess,time,traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
BASE=['/public/software/singularity-ce-4.3.4/bin/singularity','exec','--bind','/public/home/yuzelu/opt/eda:/eda:ro']
SIF='/public/home/yuzelu/opt/eda/containers/orfs-26Q1-repacked.sif'
LIB=Path('/public/home/yuzelu/RuizhiLiang/issue80-block-circuit-20261025/nangate45-reference/NangateOpenCellLibrary_typical.lib')
COMMON=['project/rtl/runtime_cache/sfu84.sv','project/rtl/runtime_cache/mul84.sv','project/rtl/wide_service/memory_link.sv','project/rtl/norm_service/store82.sv']
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def put(p,x):p.write_text(json.dumps(x,indent=2)+'\n',newline='\n')
def adapted(family,style):
 text=(ROOT/'project/rtl/attention_width/attention110.sv').read_text()
 assert text.count('module attention110 #(parameter STYLE=0)(')==1
 text=text.replace('module attention110 #(parameter STYLE=0)(',f'module attention{family} #(parameter STYLE={style})(')
 if family==102:
  # Restore exactly the original standalone 102 native multiplier bank. No extra bank.
  old='output reg signed [31:0] obs_x,obs_y,output reg [63:0] obs_sum,\n output wire [63:0] byte_a,byte_b,input wire [127:0] byte_p);'
  new='output reg signed [31:0] obs_x,obs_y,output reg [63:0] obs_sum);'
  assert text.count(old)==1;text=text.replace(old,new)
  old='assign byte_a[8*g+:8]=aa[g];assign byte_b[8*g+:8]=bb[g];assign pp[g]=$signed(byte_p[16*g+:16]);'
  assert text.count(old)==1;text=text.replace(old,'assign pp[g]=aa[g]*bb[g];')
 return text

def main():
 p=argparse.ArgumentParser();p.add_argument('task',choices=['build','sim','map']);p.add_argument('--family',type=int,choices=[102,106],required=True);p.add_argument('--style',type=int,choices=[0,1,2],required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--stall',type=int,default=0);p.add_argument('--pilot',type=int,default=0);p.add_argument('--suite',choices=['pilot','qualification'],default='pilot');p.add_argument('--input',type=Path);p.add_argument('--build',type=Path);a=p.parse_args();bd=json.loads((ROOT/'binding.json').read_text())
 for n,h in bd['sources'].items():assert sha(ROOT/n)==h,'source '+n
 a.out.mkdir(exist_ok=False,parents=True);m={'status':'ERROR','source':bd,'family':a.family,'style':a.style,'profile':0,'stall':a.stall,'task':a.task,'pilot':a.pilot,'suite':a.suite}
 prefix=[*BASE,'--pwd',str(a.out),SIF];top='chain102'if a.family==102 else'shared106';folder='attention_rtl'if a.family==102 else'shared_services'
 def cmd(tag,args):
  argv=[*prefix,*map(str,args)];start=time.monotonic()
  with(a.out/(tag+'.log')).open('w')as f:r=subprocess.run(argv,stdout=f,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,timeout=1800)
  put(a.out/(tag+'-command.json'),{'argv':argv,'exit':r.returncode,'seconds':time.monotonic()-start})
  if r.returncode:raise ValueError('failed '+tag)
 try:
  source=a.out/('attention'+str(a.family)+'.sv');source.write_text(adapted(a.family,a.style),newline='\n');m['adapter_sha256']=sha(source)
  sv=[source,ROOT/'project/rtl/attention/chain102.sv']if a.family==102 else[source,*[ROOT/'project/rtl/shared_services'/n for n in('mfront106.sv','norm106.sv','m106.sv','a106.sv','r106.sv','shared106.sv')],ROOT/'project/rtl/v_consumer/vprep97.sv']
  sv +=[ROOT/n for n in COMMON];m['compiled_sources']={str(n):sha(n)for n in sv}
  if a.task=='build':
   driver=ROOT/f'project/experiments/{folder}'/('qualification.cpp'if a.suite=='qualification'else'sim.cpp');m['compiled_sources'][str(driver)]=sha(driver)
   cmd('build',['/eda/verilator-5.042/bin/verilator','--cc','--exe','--build','-j','2','-Wno-fatal','--top-module',top,'--prefix','V'+top,'--Mdir',a.out/'obj','-CFLAGS','-std=c++17 -O2',*sv,driver]);m.update(status='BUILT_NOT_EXECUTED',binary_sha256=sha(a.out/'obj'/('V'+top)))
  elif a.task=='sim':
   bm=json.loads((a.build/'manifest.json').read_text());im=json.loads((a.input/'manifest.json').read_text());assert bm['status']=='BUILT_NOT_EXECUTED'and(bm['family'],bm['style'],bm['suite'])==(a.family,a.style,a.suite)
   assert bm['adapter_sha256']==m['adapter_sha256']and bm['source']==bd and sha(a.build/'obj'/('V'+top))==bm['binary_sha256']
   for e in im['artifacts']:assert sha(a.input/e['path'])==e['sha256']
   cmd('simulation',[a.build/'obj'/('V'+top),a.input/'vectors.tsv',a.out/'actual.jsonl',a.stall,a.pilot]);m.update(status='RTL_EXECUTED_NOT_RECEIVED',input_manifest_sha256=sha(a.input/'manifest.json'),build_manifest_sha256=sha(a.build/'manifest.json'))
  else:
   script='read_verilog -sv '+' '.join(map(str,sv))+f'\nhierarchy -top {top}\nproc\nopt\nwreduce\nmemory_dff\nmemory_collect\nopt_clean\ncheck -assert\nwrite_json '+str(a.out/'generic.json')+'\n'
   (a.out/'generic.ys').write_text(script,newline='\n');cmd('generic',['yosys','-s',a.out/'generic.ys'])
   script='read_liberty -lib '+str(LIB)+'\nread_verilog -sv '+' '.join(map(str,sv))+f'\nhierarchy -top {top}\nblackbox store82\nsynth -top {top} -flatten -noabc\nabc -fast -exe /usr/local/bin/../bin/yosys-abc\nopt -fast\ndfflibmap -liberty '+str(LIB)+'\nabc -exe /usr/local/bin/../bin/yosys-abc -liberty '+str(LIB)+'\nclean\ncheck -assert\ntee -o '+str(a.out/'stat.json')+' stat -liberty '+str(LIB)+' -json\nwrite_json '+str(a.out/'mapped.json')+'\n'
   (a.out/'map.ys').write_text(script,newline='\n');cmd('map',['yosys','-s',a.out/'map.ys']);m.update(status='LOGIC_ONLY_MAPPED_NOT_PPA',library_sha256=sha(LIB))
 except Exception as e:m.update(error=str(e),traceback=traceback.format_exc());raise
 finally:
  m['artifacts']=[{'path':q.name,'bytes':q.stat().st_size,'sha256':sha(q)}for q in a.out.iterdir()if q.is_file()and q.name!='manifest.json'];put(a.out/'manifest.json',m)
 print(m['status'])
if __name__=='__main__':main()
