"""Independent exact-cell audit and a separately constructed all-domain SAT check."""
import argparse,copy,hashlib,json,subprocess,time,traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
SIF='/public/home/yuzelu/opt/eda/containers/orfs-26Q1-repacked.sif'
BASE=['/public/software/singularity-ce-4.3.4/bin/singularity','exec','--bind','/public/home/yuzelu/opt/eda:/eda:ro']
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def put(p,x):p.write_text(json.dumps(x,indent=2)+'\n',newline='\n')
def need(x,m):
 if not x:raise ValueError(m)
def artifacts(root,m):
 for e in m['artifacts']:
  p=(root/e['path']).resolve();need(p.is_relative_to(root.resolve())and p.stat().st_size==e['bytes']and sha(p)==e['sha256'],'artifact '+e['path'])
def source_scope():
 old=(ROOT/'project/rtl/shared_services/attention106.sv').read_text();new=(ROOT/'project/rtl/attention_width/attention110.sv').read_text()
 need(new.count('module attention110 #(parameter STYLE=0)(')==1,'unique top')
 new=new.replace('module attention110 #(parameter STYLE=0)(','module attention106(')
 # The entire implementation outside two declared expression ranges is byte-identical.
 begin=' wire signed [63:0] dotnext=';end=' wire signed [63:0] pvnext[0:7];'
 oldpart=old[old.index(begin):old.index(end)];newpart=new[new.index(' localparam QK_W='):new.index(end)]
 check=new.replace(newpart,oldpart)
 start='  assign pvnext[g]=';stop='  assign pvbad[g]='
 oldpart=old[old.index(start):old.index(stop)];newpart=check[check.index('  wire [2:0] shifts='):check.index(stop)]
 check=check.replace(newpart,oldpart)
 need(check==old,'controller/guard/ports outside declared shifts modified')
 old102=(ROOT/'project/rtl/attention/attention102.sv').read_text()
 baseline=old.replace('module attention106(','module attention102(').replace('output reg signed [31:0] obs_x,obs_y,output reg [63:0] obs_sum,\n output wire [63:0] byte_a,byte_b,input wire [127:0] byte_p);','output reg signed [31:0] obs_x,obs_y,output reg [63:0] obs_sum);').replace('assign byte_a[8*g+:8]=aa[g];assign byte_b[8*g+:8]=bb[g];assign pp[g]=$signed(byte_p[16*g+:16]);','assign pp[g]=aa[g]*bb[g];')
 need(baseline==old102,'original102 compatibility source equivalence')
 return {'unchanged_controller_guards_ports':True,'old102_exact_native8S8_adapter':True}

def check_cone(original,cone,cuts,outs):
 expected={**{n:{'direction':'input','bits':b}for n,b in cuts.items()},**{n:{'direction':'output','bits':b}for n,b in outs.items()}}
 need(cone['ports']==expected,'actual cone cut/output bit bindings')
 blocked={b for p in cuts.values()for b in p};drivers={}
 for n,c in original['cells'].items():
  if 'dff'in c['type'].lower():continue
  for p,bits in c['connections'].items():
   if c['port_directions'][p]=='output':
    for b in bits:
     if type(b)is int:need(b not in drivers,'multiple source driver');drivers[b]=n
 selected=set();pending=[b for bits in outs.values()for b in bits]
 while pending:
  b=pending.pop()
  if type(b)is not int or b in blocked:continue
  need(b in drivers,'missing true cone driver');n=drivers[b]
  if n in selected:continue
  selected.add(n);c=original['cells'][n]
  for p,bs in c['connections'].items():
   if c['port_directions'][p]=='input':pending.extend(bs)
 need(cone['cells']=={n:original['cells'][n]for n in selected},'exact original cells/parameters/ports, no substitute model')

def audit(proof):
 m=json.loads((proof/'manifest.json').read_text());artifacts(proof,m);need(m['status']=='PASS_ACTUAL_RTL_ALL_DOMAIN_AND_INDUCTIVE_LIMBS','proof status')
 for n,h in m['source']['sources'].items():need(sha(ROOT/n)==h,'proof source '+n)
 binding=json.loads((proof/'extraction.json').read_text());math=json.loads((proof/'math-cones.json').read_text())['modules']; invs={}
 for v in ['original',0,1,2]:
  tag='v'+str(v);top='attention106'if v=='original'else'attention110';raw=json.loads((proof/(tag+'-proc.json')).read_text())['modules'][top];net=raw['netnames'];cuts={n:net[n]['bits']for n in ['byte_p','accum','limb','plimb','vlimb']}
  cuts.update({'v'+str(i):net[f'vacc[{i}]']['bits']for i in range(8)})
  outs={n:net[n]['bits']for n in['dotnext','pvbad']};outs.update({'p'+str(i):net[f'pvnext[{i}]']['bits']for i in range(8)})
  prefixes=binding[tag]['math']['prefixes'];need([x['indices']for x in prefixes]==[list(range(k))for k in range(2,9)],'declared prefixes')
  for i,x in enumerate(prefixes):need(x['bits']==raw['cells'][x['cell']]['connections']['Y']and raw['cells'][x['cell']]['type']=='$add','actual prefix output');outs['partial'+str(i)]=x['bits']
  check_cone(raw,math['math_'+tag],cuts,outs)
  inv=json.loads((proof/(tag+'-inv.json')).read_text())['modules']['inv_'+tag];icuts={n:p['bits']for n,p in raw['ports'].items()if p['direction']=='input'};iouts={}
  for i,(n,c)in enumerate(raw['cells'].items()):
   if 'dff'in c['type'].lower():
    need(c['type']=='$dff','actual FF kind');key=next((name for name in ['limb','plimb','vlimb']if c['connections']['Q']==net[name]['bits']),'q'+str(i));icuts[key]=c['connections']['Q']
    if key in ['limb','plimb','vlimb']:iouts['next_'+key]=c['connections']['D']
  need(len(iouts)==3,'all real limb FFs');check_cone(raw,inv,icuts,iouts);invs['inv_'+tag]=inv
  source=ROOT/('project/rtl/shared_services/attention106.sv'if v=='original'else'project/rtl/attention_width/attention110.sv')
  expected='read_verilog -sv '+str(source)+'\n'+('chparam -set STYLE '+str(v)+' '+top+'\n'if v!='original'else'')+'hierarchy -top '+top+'\nproc\nopt_expr\nopt_clean\nwrite_json '+str(proof/(tag+'-proc.json'))+'\n'
  # The historical phase has its own root; allow precisely that immutable phase prefix.
  recorded=(proof/(tag+'-proc.ys')).read_text();oldroot=recorded.split('read_verilog -sv ',1)[1].split('/project/',1)[0]
  need(recorded==expected.replace(str(ROOT),oldroot),'exact synthesis command, no source replacement')
  cmd=json.loads((proof/(tag+'-proc-command.json')).read_text());need(type(cmd['exit'])is int and cmd['exit']==0 and cmd['argv'][-3:]==['yosys','-s',str(proof/(tag+'-proc.ys'))],'actual proc execution')
 return math,invs,m

def check_text(modules,kind):
 # New property construction, independent of the producer's monitor/extraction functions.
 first=next(iter(modules.values()));inputs={n:p for n,p in first['ports'].items()if p['direction']=='input'}
 # FSM register numbering varies per variant, so each invariant is separately checked.
 text='module independent('+','.join('input wire ['+str(len(p['bits'])-1)+':0] '+n for n,p in inputs.items())+',output wire ok);\n';checks=[]
 for j,(name,m)in enumerate(modules.items()):
  conn=[]
  for n,p in m['ports'].items():
   wire=n if p['direction']=='input'else f'o{j}_{n}'
   if p['direction']=='output':text+=f'wire [{len(p["bits"])-1}:0] {wire};\n'
   conn.append('.'+n+'('+wire+')')
  text+=name+' dut'+str(j)+'('+','.join(conn)+');\n'
  if kind=='math':
   for k in range(7):
    expr='+'.join('$signed({{48{byte_p['+str(16*i+15)+']}},byte_p['+str(16*i)+'+:16]})'for i in range(k+2));text+=f'wire signed [63:0] sum{j}_{k}={expr};\n';checks +=[f'($signed(o{j}_partial{k})==sum{j}_{k})']
   if j:
    eq='&&'.join('(o0_'+n+'==o'+str(j)+'_'+n+')'for n,p in first['ports'].items()if p['direction']=='output');checks +=['((limb>2)||('+eq+'))'if j==3 else '('+eq+')']
  else:
   reset='&&'.join(f'o{j}_next_{n}==0'for n in ['limb','plimb','vlimb']);pre='&&'.join(n+'<3'for n in ['limb','plimb','vlimb']);post='&&'.join(f'o{j}_next_{n}<3'for n in ['limb','plimb','vlimb']);checks +=['(reset?('+reset+'):(!('+pre+')||('+post+')))']
 text+='assign ok='+ '&&'.join(checks)+';\nendmodule\n';return text

def main():
 p=argparse.ArgumentParser();p.add_argument('--proof',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(exist_ok=False,parents=True);receipt={'status':'ERROR'}
 try:
  scope=source_scope();math,invs,m=audit(a.proof);commands=[]
  targets=[('math',math)]+[(n,{n:v})for n,v in invs.items()]
  for name,mods in targets:
   inp=a.out/(name+'.json');put(inp,{'modules':mods});mon=a.out/(name+'.sv');mon.write_text(check_text(mods,'math'if name=='math'else'inv'),newline='\n')
   ys=a.out/(name+'.ys');ys.write_text(f'read_json {inp}\nread_verilog {mon}\nprep -top independent\nflatten\nopt_clean\nsat -verify -prove ok 1\n',newline='\n');argv=[*BASE,'--pwd',str(a.out),SIF,'yosys','-s',str(ys)];start=time.monotonic()
   with(a.out/(name+'.log')).open('w')as f:r=subprocess.run(argv,stdout=f,stderr=subprocess.STDOUT,timeout=600)
   commands.append({'name':name,'argv':argv,'exit':r.returncode,'seconds':time.monotonic()-start});need(r.returncode==0 and 'SUCCESS'in(a.out/(name+'.log')).read_text(),'independent real SAT')
  receipt.update(status='PASS_INDEPENDENT_ACTUAL_CONES_AND_ALL_DOMAIN_SAT',source_scope=scope,proof_manifest_sha256=sha(a.proof/'manifest.json'),proof_source=m['source'],commands=commands,receiver_source=json.loads((ROOT/'binding.json').read_text()))
 except Exception as e:receipt.update(error=str(e),traceback=traceback.format_exc());raise
 finally:
  receipt['artifacts']=[{'path':p.name,'bytes':p.stat().st_size,'sha256':sha(p)}for p in a.out.iterdir()if p.is_file()and p.name!='receipt.json'];put(a.out/'receipt.json',receipt)
 print(receipt['status'])
if __name__=='__main__':main()
