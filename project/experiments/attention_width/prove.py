"""Extract exact proc cells and universally prove arithmetic and real FF invariants."""
import argparse,copy,hashlib,json,subprocess,time,traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
PREFIX=['/public/software/singularity-ce-4.3.4/bin/singularity','exec','--bind','/public/home/yuzelu/opt/eda:/eda:ro']
SIF='/public/home/yuzelu/opt/eda/containers/orfs-26Q1-repacked.sif'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def put(p,x):p.write_text(json.dumps(x,indent=2)+'\n',newline='\n')
def number(v):return int(v,2)if isinstance(v,str)else v

def extract(m,name,cuts,outputs):
 cells=m['cells'];driver={};bits={b for bs in cuts.values()for b in bs if isinstance(b,int)};chosen=set()
 for n,c in cells.items():
  if 'dff'in c['type'].lower():continue
  for p,bs in c['connections'].items():
   if c['port_directions'][p]=='output':
    for b in bs:
     if isinstance(b,int):
      if b in driver:raise ValueError('multiple driver')
      driver[b]=n
 def visit(b):
  if not isinstance(b,int)or b in bits:return
  n=driver.get(b)
  if n is None:raise ValueError('unbound real cone bit '+str(b))
  if n in chosen:return
  chosen.add(n)
  for p,bs in cells[n]['connections'].items():
   if cells[n]['port_directions'][p]=='input':
    for v in bs:visit(v)
 for bs in outputs.values():
  for b in bs:visit(b)
 ports={**{n:{'direction':'input','bits':bs}for n,bs in cuts.items()},**{n:{'direction':'output','bits':bs}for n,bs in outputs.items()}}
 module={'attributes':{},'ports':ports,'cells':{n:copy.deepcopy(cells[n])for n in sorted(chosen)},'netnames':{n:{'hide_name':0,'bits':p['bits'],'attributes':{}}for n,p in ports.items()}}
 return {'creator':'Exact original proc cell/pin cone, no replacement arithmetic/FSM','modules':{name:module}}

def mathcone(m,name):
 nets=m['netnames'];cuts={n:nets[n]['bits']for n in ['byte_p','accum','limb','plimb','vlimb']}
 for i in range(8):cuts['v'+str(i)]=nets[f'vacc[{i}]']['bits']
 out={'dotnext':nets['dotnext']['bits'],'pvbad':nets['pvbad']['bits']}
 for i in range(8):out['p'+str(i)]=nets[f'pvnext[{i}]']['bits']
 partcone=extract(m,'part',cuts,{'part':nets['part']['bits']})['modules']['part'];driver={b:n for n,c in partcone['cells'].items()for p,bs in c['connections'].items()if c['port_directions'][p]=='output'for b in bs if isinstance(b,int)}
 leaf={b:i//16 for i,b in enumerate(nets['byte_p']['bits'])};prefixes=[]
 def leaves(bs,seen=None):
  result=set();seen=set()if seen is None else seen
  for b in bs:
   if b in leaf:result.add(leaf[b]);continue
   if not isinstance(b,int):continue
   n=driver.get(b)
   if n is None or n in seen:continue
   seen.add(n);c=partcone['cells'][n]
   for p,x in c['connections'].items():
    if c['port_directions'][p]=='input':result|=leaves(x,seen)
  return result
 for n,c in partcone['cells'].items():
  if c['type']=='$add':
   assert number(c['parameters']['Y_WIDTH'])==32
   which=sorted(leaves(c['connections']['Y']));prefixes.append((which,n,c['connections']['Y']))
 prefixes.sort(key=lambda v:len(v[0]));assert [x[0]for x in prefixes]==[list(range(k))for k in range(2,9)],prefixes
 for k,(_,_,bs)in enumerate(prefixes):out['partial'+str(k)]=bs
 result=extract(m,name,cuts,out)
 return result,{'cuts':cuts,'outputs':out,'prefixes':[{'indices':x,'cell':n,'bits':bs}for x,n,bs in prefixes],'original_cells':sorted(result['modules'][name]['cells'])}

def invariant(m,name):
 cuts={n:p['bits']for n,p in m['ports'].items()if p['direction']=='input'};outs={};ffbind={}
 targets={n:m['netnames'][n]['bits']for n in ['limb','plimb','vlimb']}
 for i,(n,c)in enumerate(m['cells'].items()):
  if 'dff'in c['type'].lower():
   assert c['type']=='$dff',c['type'];q=c['connections']['Q'];key=next((k for k,bs in targets.items()if bs==q),'q'+str(i));cuts[key]=q
   if key in targets:outs['next_'+key]=c['connections']['D'];ffbind[key]={'cell':n,'Q':q,'D':c['connections']['D']}
 assert set(ffbind)==set(targets)
 result=extract(m,name,cuts,outs)
 return result,{'cuts':cuts,'outputs':outs,'actual_FF':ffbind,'original_cells':sorted(result['modules'][name]['cells'])}

def decl(n,p,direction):return direction+' wire ['+str(len(p['bits'])-1)+':0] '+n

def math_monitor(mods):
 first=next(iter(mods.values()));ports=first['ports'];inputs={n:p for n,p in ports.items()if p['direction']=='input'}
 text='module check_math('+','.join([decl(n,p,'input')for n,p in inputs.items()]+['output wire proof_ok'])+');\n';checks=[]
 for j,(name,m)in enumerate(mods.items()):
  conn=[]
  for n,p in m['ports'].items():
   w=n if p['direction']=='input'else f'x{j}_{n}';conn.append('.'+n+'('+w+')')
   if p['direction']=='output':text+='wire ['+str(len(p['bits'])-1)+':0] '+w+';\n'
  text+=name+' i'+str(j)+'('+','.join(conn)+');\n'
  for k in range(7):
   expr='+'.join('$signed({{48{byte_p['+str(i*16+15)+']}},byte_p['+str(i*16)+'+:16]})'for i in range(k+2))
   text+=f'wire signed [63:0] wide{j}_{k}={expr};\n'
   checks.append(f'($signed(x{j}_partial{k})==wide{j}_{k})')
  if j:
   eq='&&'.join(f'(x0_{n}==x{j}_{n})'for n,p in ports.items()if p['direction']=='output')
   # Full-domain original->STYLE0/1; narrowed QK domain justified separately.
   checks.append(('(limb>2)||('+eq+')')if j==3 else '('+eq+')')
 text+='assign proof_ok='+('&&'.join('('+x+')'for x in checks))+';\nendmodule\n'
 return text

def inv_monitor(name,m):
 inp={n:p for n,p in m['ports'].items()if p['direction']=='input'};text='module check_inv('+','.join([decl(n,p,'input')for n,p in inp.items()]+['output wire proof_ok'])+');\n';conn=[]
 for n,p in m['ports'].items():
  if p['direction']=='output':text+='wire ['+str(len(p['bits'])-1)+':0] '+n+';\n'
  conn.append('.'+n+'('+n+')')
 text+=name+' dut('+','.join(conn)+');\n';base='&&'.join('next_'+n+'==0'for n in ['limb','plimb','vlimb']);ante='&&'.join(n+'<=2'for n in ['limb','plimb','vlimb']);succ='&&'.join('next_'+n+'<=2'for n in ['limb','plimb','vlimb'])
 text+='assign proof_ok=reset?('+base+'):(!('+ante+')||('+succ+'));\nendmodule\n';return text

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(exist_ok=False,parents=True);bd=json.loads((ROOT/'binding.json').read_text());receipt={'status':'ERROR','source':bd}
 for n,h in bd['sources'].items():assert sha(ROOT/n)==h
 def run(tag,script):
  ys=a.out/(tag+'.ys');ys.write_text(script,newline='\n');argv=[*PREFIX,'--pwd',str(a.out),SIF,'yosys','-s',str(ys)];start=time.monotonic()
  with(a.out/(tag+'.log')).open('w')as f:r=subprocess.run(argv,stdout=f,stderr=subprocess.STDOUT,timeout=600)
  put(a.out/(tag+'-command.json'),{'argv':argv,'exit':r.returncode,'seconds':time.monotonic()-start})
  if r.returncode:raise ValueError('actual Yosys failed '+tag)
  if tag.startswith('sat')and 'SUCCESS'not in(a.out/(tag+'.log')).read_text():raise ValueError('actual SAT success missing')
 try:
  modules={};bindings={};raws={}
  for v in ['original',0,1,2]:
   tag='v'+str(v);source=ROOT/('project/rtl/shared_services/attention106.sv'if v=='original'else'project/rtl/attention_width/attention110.sv');top='attention106'if v=='original'else'attention110';out=a.out/(tag+'-proc.json')
   script='read_verilog -sv '+str(source)+'\n'+('chparam -set STYLE '+str(v)+' '+top+'\n'if v!='original'else'')+'hierarchy -top '+top+'\nproc\nopt_expr\nopt_clean\nwrite_json '+str(out)+'\n';run(tag+'-proc',script);m=json.loads(out.read_text())['modules'][top];raws[tag]=m
   cone,b=mathcone(m,'math_'+tag);modules.update(cone['modules']);bindings[tag]={'proc_sha256':sha(out),'math':b}
   inv,ib=invariant(m,'inv_'+tag);bindings[tag]['invariant']=ib;put(a.out/(tag+'-inv.json'),inv);monitor=a.out/(tag+'-inv.v');monitor.write_text(inv_monitor('inv_'+tag,inv['modules']['inv_'+tag]),newline='\n')
   run('sat-'+tag+'-inv','read_json '+str(a.out/(tag+'-inv.json'))+'\nread_verilog '+str(monitor)+'\nprep -top check_inv\nflatten\nopt_clean\nsat -verify -prove proof_ok 1 -show-inputs -show-outputs -dump_json '+str(a.out/(tag+'-inv-counterexample.json'))+'\n')
  put(a.out/'math-cones.json',{'modules':modules});(a.out/'math-monitor.v').write_text(math_monitor(modules),newline='\n')
  run('sat-math','read_json '+str(a.out/'math-cones.json')+'\nread_verilog '+str(a.out/'math-monitor.v')+'\nprep -top check_math\nflatten\nopt_clean\nsat -verify -prove proof_ok 1 -show-inputs -show-outputs -dump_json '+str(a.out/'math-counterexample.json')+'\n')
  put(a.out/'extraction.json',bindings);receipt.update(status='PASS_ACTUAL_RTL_ALL_DOMAIN_AND_INDUCTIVE_LIMBS',variants=['original',0,1,2],limits=['2-state bitvector SAT, assumes correctly clocked reset as original design.','No physical timing/liveness/soft-error guarantee; limb3 excluded only through real reset+one-step inductive invariant.','Original prefix additions, full64 final values and per-limb INT32 guards preserved.'])
 except Exception as e:receipt.update(error=str(e),traceback=traceback.format_exc());raise
 finally:
  receipt['artifacts']=[{'path':p.name,'bytes':p.stat().st_size,'sha256':sha(p)}for p in a.out.iterdir()if p.is_file()and p.name!='manifest.json'];put(a.out/'manifest.json',receipt)
 print(receipt['status'])
if __name__=='__main__':main()
