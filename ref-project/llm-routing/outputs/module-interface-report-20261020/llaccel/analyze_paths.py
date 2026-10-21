"""Frozen final physical connectivity; writes only this standalone study.

Trace combinational payload dependencies, MUX data pins only; all sequential
elements are barriers. Endpoints are named data-state pins, NOT recovered RTL
interface wires. Whole physical nets, including off-path branches, are counted.
"""
from pathlib import Path
from collections import defaultdict, Counter, deque
from array import array
import csv, gzip, hashlib, json, re, time
import numpy as np
from scipy.sparse import csr_matrix

P=Path(__file__).resolve().parent
SRC=P.parents[1]/'llaccel-engine-analysis-20261020'
DATA=SRC/'compact_physical_evidence.jsonl.gz'
MODELS=json.loads((P/'liberty_models.json').read_text())
LABELS={
 'GEMM_WEIGHT':'GEMM：bank 读数据 → 权重缓冲 D',
 'GEMM_AUX':'GEMM：bank 读数据 → 乘法首级／参数状态 D',
 'VECTOR_A':'VECTOR：bank 读数据 → 读口 0 缓冲 D',
 'VECTOR_B':'VECTOR：bank 读数据 → 读口 1 缓冲 D',
 'GEMM_WRITE':'GEMM：输出 FIFO 数据 Q → bank 写数据',
 'VECTOR_WRITE':'VECTOR：结果寄存器 Q → bank 写数据',
}

def rows():
 with gzip.open(DATA,'rt',encoding='utf8') as f:
  for line in f:yield json.loads(line)

def norm(s):return s.replace('\\','')
def dump(name,obj):
 (P/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf8')
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
 return h.hexdigest()

def main():
 t=time.time();cn=[];cm=[];idx={};boxes=[];header=None
 for a in rows():
  if isinstance(a,dict):header=a;continue
  if a[0]!='c':break
  idx[a[2]]=len(cn);cn.append(norm(a[2]));cm.append(a[3]);boxes.append(a[4])
 print('cells',len(cn),flush=True)
 pins=[None]*len(cn);netlayers={};netnames={};drivercount={};bank=defaultdict(set);maxid=0
 for a in rows():
  if not isinstance(a,list) or a[0]!='n':continue
  _,ni,name,cat,ds,ls,bs,layers,attrs=a;maxid=max(maxid,ni)
  netlayers[ni]=layers;netnames[ni]=norm(name)
  drivercount[ni]=len(ds)+sum(x[1]=='driver' for x in bs)
  for bn,role,io in bs:
   if bn.startswith('bank_'):bank[bn.split('[')[0]].add(ni)
  if cat in ('CLOCK','RESET','POWER','GROUND') or any(x in ('clock','reset') for x in attrs):continue
  for name,pin in ds+ls:
   j=idx.get(name)
   if j is None:continue
   if pins[j] is None:pins[j]={}
   if pin in pins[j]:assert pins[j][pin]==ni,(name,pin)
   pins[j][pin]=ni
 print('pins loaded',round(time.time()-t,1),'s',flush=True)
 starts=defaultdict(set);ends=defaultdict(set);statepins=defaultdict(list)
 for j,name in enumerate(cn):
  pp=pins[j] or {};m=MODELS.get(cm[j],{})
  if m.get('kind')!='SEQ':continue
  keys=[]
  if name.startswith('u_gemm.wbuf['):keys.append('GEMM_WEIGHT')
  if any(name.startswith('u_gemm.'+s+'[') for s in ['prod','rq_m','rq_s','bias_v','aux_hold']):keys.append('GEMM_AUX')
  if name.startswith(('u_vec.u_f0.mem[','u_vec.u_s0.hold[')):keys.append('VECTOR_A')
  if name.startswith(('u_vec.u_f1.mem[','u_vec.u_s1.hold[')):keys.append('VECTOR_B')
  for k in keys:
   for pin in m.get('data',[]):
    if pin in pp:ends[k].add(pp[pin]);statepins[k].append([name,pin,pp[pin]])
  k=None
  if name.startswith('u_gemm.u_out.mem['):
   ns=re.findall(r'\[(\d+)\]',name)
   if len(ns)>=2 and int(ns[1])<256:k='GEMM_WRITE'
  if name.startswith('u_vec.wr_data_r['):k='VECTOR_WRITE'
  if k:
   for pin in m.get('outputs',[]):
    if pin in pp:starts[k].add(pp[pin]);statepins[k].append([name,pin,pp[pin]])
 for k in LABELS:
  if k.endswith('WRITE'):ends[k]=bank['bank_wdata']
  else:starts[k]=bank['bank_rdata']
 aa=array('I');bb=array('I');gate=array('I');unsupported=Counter();badarcs=0
 for j,pp in enumerate(pins):
  if not pp:continue
  m=MODELS.get(cm[j])
  if m is None:unsupported[cm[j]]+=1;continue
  if m.get('kind')!='COMB':continue
  for op in m.get('outputs',[]):
   if op not in pp:continue
   expr=m.get('functions',{}).get(op,'')
   for ip in m.get('inputs',[]):
    if ip not in pp or not re.search(r'(?<![A-Za-z0-9_])'+re.escape(ip)+r'(?![A-Za-z0-9_])',expr):continue
    if cm[j].startswith('MUX2_') and ip=='S':continue
    a,b=pp[ip],pp[op]
    if a==b:continue
    if drivercount[a]!=1 or drivercount[b]!=1:badarcs+=1;continue
    aa.append(a);bb.append(b);gate.append(j)
 n=maxid+1
 fwd=csr_matrix((np.ones(len(aa),dtype=np.uint8),(np.asarray(aa),np.asarray(bb))),shape=(n,n));fwd.sum_duplicates()
 rev=fwd.transpose().tocsr()
 def reach(ss,graph):
  seen=np.zeros(n,dtype=bool);q=deque(ss)
  for i in ss:seen[i]=True
  while q:
   i=q.popleft()
   for v in graph.indices[graph.indptr[i]:graph.indptr[i+1]]:
    if not seen[v]:seen[v]=True;q.append(int(v))
  return seen
 print('arcs',len(aa),'unsupported',unsupported,flush=True)
 # Model-verified single-input BUF/INV components, for the boundary-near view.
 ua=array('I');ub=array('I')
 for j,pp in enumerate(pins):
  m=MODELS.get(cm[j],{})
  if not pp or m.get('kind')!='COMB' or len(m.get('inputs',[]))!=1 or len(m.get('outputs',[]))!=1:continue
  ip,op=m['inputs'][0],m['outputs'][0]
  if re.sub(r'[\s()!~]','',m.get('functions',{}).get(op,''))!=ip:continue
  if ip in pp and op in pp and drivercount[pp[ip]]==drivercount[pp[op]]==1:ua.append(pp[ip]);ub.append(pp[op])
 uf=csr_matrix((np.ones(2*len(ua),dtype=np.uint8),(np.r_[ua,ub],np.r_[ub,ua])),shape=(n,n))
 groups={};coverage={};pathcells={};evidence={}
 for k in LABELS:
  fw=reach(starts[k],fwd);bw=reach(ends[k],rev);path=fw&bw
  selected=set(int(i) for i in np.flatnonzero(path));groups[k]=selected
  st=set(starts[k])&selected;en=set(ends[k])&selected
  # This is the last/first data-register electrical connection, not an RTL port.
  terminal=st if k.endswith('WRITE') else en
  groups[k+'_STATE_DIRECT']=terminal
  groups[k+'_STATE_LEG']=set(int(i) for i in np.flatnonzero(reach(terminal,uf)&path))
  boundary=en if k.endswith('WRITE') else st
  groups[k+'_BANK_LEG']=set(int(i) for i in np.flatnonzero(reach(boundary,uf)&path))
  coverage[k]={'start_nets':len(starts[k]),'starts_reaching_end':len(st),'end_nets':len(ends[k]),'ends_reached':len(en),'state_pins':len(statepins[k]),'state_pins_on_path':sum(ni in selected for _,_,ni in statepins[k])}
  coverage[k]['state_cells']=len({name for name,pin,ni in statepins[k]})
  coverage[k]['state_cells_on_path']=len({name for name,pin,ni in statepins[k] if ni in selected})
  mask=path[np.asarray(aa)] & path[np.asarray(bb)]
  used=set(int(gate[i]) for i in np.flatnonzero(mask));pathcells[k]=[[cn[j],cm[j],boxes[j]] for j in sorted(used)]
  evidence[k]=dict(starts=sorted(st),ends=sorted(en),state_pins=statepins[k])
  print(k,coverage[k],'nets',len(selected),flush=True)
 for k,ss in bank.items():groups[k]=ss
 results={};table=[]
 for k,ss in groups.items():
  layers=Counter();cnt=Counter();lo={};hi={}
  for i in ss:
   for layer,l in netlayers[i].items():
    layers[layer]+=l
    if l>0:cnt[layer]+=1;lo[layer]=min(lo.get(layer,l),l);hi[layer]=max(hi.get(layer,l),l)
  total=sum(layers.values())
  results[k]={'nets':len(ss),'length_um':total/2000,'layers_um':{l:v/2000 for l,v in sorted(layers.items())},'M4plus_pct':100*sum(v for l,v in layers.items() if int(re.sub(r'\D','',l))>=4)/total if total else 0,'M2M3_pct':100*sum(layers[x] for x in ['metal2','metal3'])/total if total else 0}
  for l,v in sorted(layers.items()):
   table.append(dict(group=k,layer=l,length_um=v/2000,nets=cnt[l],mean_um=v/2000/cnt[l] if cnt[l] else 0,min_um=lo.get(l,0)/2000,max_um=hi.get(l,0)/2000))
 # Whole-net shared portions: overlaps are explicit and must not be added.
 overlap={}
 for a in LABELS:
  for b in LABELS:
   if a>=b:continue
   ss=groups[a]&groups[b]
   if ss:overlap[a+' & '+b]={'nets':len(ss),'length_um':sum(sum(netlayers[i].values()) for i in ss)/2000}
 payload={'labels':LABELS,'source':header,'input_sha256':sha(DATA),'liberty_sha256':sha(P/'liberty_models.json'),'results':results,'coverage':coverage,'overlap':overlap,'method':'Combinational function dependencies; MUX A/B only; no sequential crossings. Named register data D/Q to actual SRAM bank top pins. Whole net length including off-path branches; not recovered RTL port nets, not timing-sensitized paths. Read destinations include GEMM multiplier first-stage D. Register-local view follows BUF/INV only within full path.','validation':{'unsupported_masters':dict(unsupported),'rejected_non_single_driver_arcs':badarcs,'cells':len(cn),'arcs':len(aa),'global_length_um':sum(sum(x.values()) for x in netlayers.values())/2000,'bank_port_net_counts':{k:len(v) for k,v in bank.items()},'state_pins_unreached':{k:v['state_pins']-v['state_pins_on_path'] for k,v in coverage.items()}}}
 dump('summary.json',payload);dump('endpoint_evidence.json',evidence)
 with (P/'layer_statistics.csv').open('w',newline='',encoding='utf-8-sig') as f:
  w=csv.DictWriter(f,fieldnames=list(table[0]));w.writeheader();w.writerows(table)
 selected=set().union(*groups.values())
 with gzip.open(P/'path_net_evidence.jsonl.gz','wt',encoding='utf8') as f:
  for ni in sorted(selected):f.write(json.dumps({'id':ni,'name':netnames[ni],'layers_dbu':netlayers[ni],'groups':[k for k,v in groups.items() if ni in v]},separators=(',',':'))+'\n')
 with gzip.open(P/'path_cells.json.gz','wt',encoding='utf8') as f:json.dump(pathcells,f)
 print('done',round(time.time()-t,1),'s',flush=True)

if __name__=='__main__':main()
