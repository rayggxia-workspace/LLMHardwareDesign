"""Candidate execution binding plus unchanged independent integer/finite-port receivers."""
import argparse,hashlib,importlib.util,json,traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def need(x,s):
 if not x:raise ValueError(s)
def put(p,x):p.write_text(json.dumps(x,indent=2)+'\n',newline='\n')
def module(name,rel):
 s=importlib.util.spec_from_file_location(name,ROOT/rel);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def bound(root):
 m=json.loads((root/'manifest.json').read_text());need(len(m['artifacts'])==len({e['path']for e in m['artifacts']}),'unique artifacts')
 for e in m['artifacts']:
  p=(root/e['path']).resolve();need(p.is_relative_to(root.resolve())and p.stat().st_size==e['bytes']and sha(p)==e['sha256'],'artifact '+e['path'])
 return m

def binding(run):
 m=bound(run);need(type(m['family'])is int and m['family']in[102,106],'family exact');need(type(m['style'])is int and m['style']in[0,1,2],'style exact');family=m['family'];style=m['style'];top='chain102'if family==102 else'shared106';folder='attention_rtl'if family==102 else'shared_services'
 command=json.loads((run/'simulation-command.json').read_text());binary=Path(command['argv'][-5]);build=binary.parent.parent;bm=bound(build)
 need(bm['family']==family and bm['style']==style and bm['suite']==m['suite'],'actual binary variant/driver');need(m['build_manifest_sha256']==sha(build/'manifest.json'),'actual executed build manifest')
 candidate=build/f'attention{family}.sv';text=candidate.read_text();new=(ROOT/'project/rtl/attention_width/attention110.sv').read_text()
 # Independently reverse only the allowed standalone adapter; compare canonical proven RTL.
 want_header=f'module attention{family} #(parameter STYLE={style})(';need(text.count(want_header)==1,'exact variant elaboration parameter')
 text=text.replace(want_header,'module attention110 #(parameter STYLE=0)(')
 if family==102:
  old='output reg signed [31:0] obs_x,obs_y,output reg [63:0] obs_sum);';need(text.count(old)==1,'native port adapter');text=text.replace(old,'output reg signed [31:0] obs_x,obs_y,output reg [63:0] obs_sum,\n output wire [63:0] byte_a,byte_b,input wire [127:0] byte_p);')
  need(text.count('assign pp[g]=aa[g]*bb[g];')==1,'native8S8 bank exact');text=text.replace('assign pp[g]=aa[g]*bb[g];','assign byte_a[8*g+:8]=aa[g];assign byte_b[8*g+:8]=bb[g];assign pp[g]=$signed(byte_p[16*g+:16]);')
 need(text==new and sha(candidate)==bm['adapter_sha256']==m['adapter_sha256'],'compiled adapter equals actual proven candidate')
 driver='qualification.cpp'if m['suite']=='qualification'else'sim.cpp';cmd=json.loads((build/'build-command.json').read_text());argv=cmd['argv'];need(type(cmd['exit'])is int and cmd['exit']==0,'actual build exit');driverpath=Path(argv[-1]);oldroot=str(driverpath).split('/project/')[0]
 expected=[str(candidate),oldroot+'/project/rtl/attention/chain102.sv']if family==102 else[str(candidate),*[oldroot+'/project/rtl/shared_services/'+n for n in('mfront106.sv','norm106.sv','m106.sv','a106.sv','r106.sv','shared106.sv')],oldroot+'/project/rtl/v_consumer/vprep97.sv']
 expected +=[oldroot+'/'+n for n in('project/rtl/runtime_cache/sfu84.sv','project/rtl/runtime_cache/mul84.sv','project/rtl/wide_service/memory_link.sv','project/rtl/norm_service/store82.sv')];expected +=[oldroot+f'/project/experiments/{folder}/'+driver]
 suffix=['/eda/verilator-5.042/bin/verilator','--cc','--exe','--build','-j','2','-Wno-fatal','--top-module',top,'--prefix','V'+top,'--Mdir',str(build/'obj'),'-CFLAGS','-std=c++17 -O2',*expected]
 need(argv[-len(suffix):]==suffix,'exact actual compiler source list and switches');need(set(bm['compiled_sources'])==set(expected),'compiled inventory keys')
 for source in expected:
  path=Path(source);need(sha(path)==bm['compiled_sources'][source],'compiled physical file SHA')
  if path!=candidate:
   rel=source[len(oldroot)+1:];need(sha(ROOT/rel)==sha(path)and bm['source']['sources'][rel]==sha(path),'current immutable baseline source '+rel)
 need(binary.name=='V'+top and sha(binary)==bm['binary_sha256'],'actual exact binary')
 return m,bm

def main():
 p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);p.add_argument('--input',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(exist_ok=False,parents=True);receipt={'status':'ERROR'}
 try:
  bd=json.loads((ROOT/'binding.json').read_text())
  for n,h in bd['sources'].items():need(sha(ROOT/n)==h,'receiver source binding')
  m,bm=binding(a.run)
  if m['family']==102:
   original=module('unmodified_a102_receiver','project/experiments/attention_rtl/receive.py');oracle=original.Oracle(a.input);r=original.receive(a.run,a.input,oracle)
  else:
   original=module('unmodified_106_receiver','project/experiments/shared_services/receive.py');oracle=original.Oracle(a.input);r=original.inspect(a.input,a.run,oracle)
  receipt.update(status='PASS110_ACTUAL_VARIANT_AND_INDEPENDENT_INTEGER_PROTOCOL',family=m['family'],style=m['style'],suite=m['suite'],stall=m['stall'],result=r,run_manifest_sha256=sha(a.run/'manifest.json'),build_manifest_sha256=sha(Path(json.loads((a.run/'simulation-command.json').read_text())['argv'][-5]).parent.parent/'manifest.json'),input_manifest_sha256=sha(a.input/'manifest.json'),receiver_source=bd)
 except Exception as e:receipt.update(error=str(e),traceback=traceback.format_exc());raise
 finally:put(a.out/'receipt.json',receipt)
 print(receipt['status'])
if __name__=='__main__':main()
