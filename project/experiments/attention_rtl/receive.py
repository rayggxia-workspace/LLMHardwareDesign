"""Independent file-level A102 receiver; no producer or RTL-model imports."""
import argparse,hashlib,json,math,shutil,traceback
from pathlib import Path
from fractions import Fraction
from decimal import Decimal,localcontext,ROUND_HALF_EVEN
import numpy as np
ROOT=Path(__file__).resolve().parents[3]
CAP=Path('/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/qwen25-gqa01')
OLD64=Path('/public/home/yuzelu/RuizhiLiang/issue64-block-v2-20261024/attention01')
RAW_SHA='e7b8162bae2e8e85962de5e46a32b656ff3e51095149810ea81a779820cf0d10'
MAN_SHA='165e8109f8025c8bfafc9079d5a9e40e688897162cf6e9ca48d337efd5c3b5e5'
LUT_SHA='659e0c81ddb592f49e27443dcfe89b9cf88439512cfba613dcd161950e5b6f80'
KEYS=set('name role epoch status length cycles macs sreads swrites kloads vloads lut_reads divides score_products wire_beats transactions mul_grants qk score exp sum P out'.split())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def put(p,x):Path(p).write_text(json.dumps(x,indent=2,allow_nan=False)+'\n',newline='\n')
def need(ok,msg):
 if not ok:raise ValueError(msg)
def integer(v,lo,hi,msg):need(type(v)is int and lo<=v<=hi,msg)
def artifacts(root,m):
 for f in m['artifacts']:
  p=(root/f['path']).resolve();need(p.is_relative_to(root.resolve()),'artifact escaped root');need(p.stat().st_size==f['bytes'] and sha(p)==f['sha256'],'artifact bytes '+f['path'])
def rne(v,s):
 if s<=0:return int(v)<<-s
 q,r=divmod(abs(int(v)),1<<s);q+=r>(1<<(s-1))or(r==(1<<(s-1))and q&1);return -q if v<0 else q
def coded(x,unit):
 bridge=np.rint(np.asarray(x,dtype=np.float64)*1048576)
 need(np.isfinite(bridge).all()and np.min(bridge)>=-(1<<31)and np.max(bridge)<1<<31,'source bridge range')
 return np.asarray([rne(int(v),unit+20)for v in bridge.flat],dtype=np.int64).reshape(bridge.shape)
def source_codes(raw,r):
 base=f"prefix{r['prefix']}.layer0.{r['mode']}.";q0=raw[base+'q'][:,r['position']];ints=np.rint(q0.astype(np.float64)*1048576).astype(np.int64);units=[];q=[]
 for row in ints:
  maximum=max(abs(int(v))for v in row);s=max(0,maximum.bit_length()-7)
  if maximum>127*(1<<s):s+=1
  units.append(s-20);q.append([rne(v,s)for v in row])
 ke=math.ceil(math.log2(float(np.max(abs(raw['calibration.layer0.full.k'].astype(np.float64))))/32767));ve=math.ceil(math.log2(float(np.max(abs(raw['calibration.layer0.full.v'].astype(np.float64))))/32767))
 return np.asarray(q,np.int64),units,ke,ve,base
class Oracle:
 def __init__(self,inp):
  self.inp=inp;self.im=json.loads((inp/'manifest.json').read_text());artifacts(inp,self.im);need(self.im['cases']==79 and self.im['real_queries']==76,'frozen case inventory');self.rows=json.loads((inp/'cases.json').read_text());self.byname={r['name']:r for r in self.rows};need(len(self.byname)==79,'unique cases')
  need(sha(CAP/'selected-raw.npz')==RAW_SHA and sha(CAP/'manifest.json')==MAN_SHA,'original capture bytes');self.raw=np.load(CAP/'selected-raw.npz',allow_pickle=False);self.cache={};self.answers={}
  b=(inp/'lut.bin').read_bytes();need(len(b)==131072 and hashlib.sha256(b[73744:81940]).hexdigest()==LUT_SHA,'actual exp object bytes');self.lut=np.frombuffer(b[73744:81940],dtype='<u4').astype(np.int64)
  old=Path('/public/home/yuzelu/RuizhiLiang/issue97-v-consumer-20261025/input02/lut.bin').read_bytes();need(b[:73744]==old[:73744]and b[81940:]==old[81940:],'old LUT words/padding unchanged')
  with localcontext() as ctx:
   ctx.prec=50;independent=[int(((-Decimal(i)/128).exp()*Decimal(1<<30)).to_integral_value(rounding=ROUND_HALF_EVEN))for i in range(2049)]
  need(np.array_equal(self.lut,independent),'independent Decimal50 LUT')
  old_manifest=json.loads((OLD64/'manifest.json').read_text());self.old_artifacts=old_manifest['artifacts']
 def answer(self,name):
  if name in self.answers:return self.answers[name]
  r=self.byname[name];n=r['length'];q=np.fromfile(self.inp/r['q'],dtype=np.int8).reshape(8,128).astype(np.int64);kall=np.fromfile(self.inp/r['k'],dtype='<i2').reshape(-1,128).astype(np.int64);vall=np.fromfile(self.inp/r['v'],dtype='<i2').reshape(-1,128).astype(np.int64);k=kall[:n];v=vall[:n]
  need(1<=n<=1056 and r['position']==n-1 and len(k)==n and len(v)==n,'frozen shape');need(np.max(abs(q))<=127 and np.max(abs(kall))<=32767 and np.max(abs(vall))<=32767,'symmetric input formats')
  if r['source']=='real':
   eq,units,ke,ve,base=source_codes(self.raw,r);need(np.array_equal(q,eq)and r['Qe']==units and r['Ke']==ke and r['Ve']==ve,'original query/unit encoding')
   if base not in self.cache:self.cache[base]=(coded(self.raw[base+'k'],ke),coded(self.raw[base+'v'],ve))
   ek,ev=self.cache[base];need(np.array_equal(kall,ek)and np.array_equal(vall,ev),'original complete KV encoding');need(r['original_npz']==str(CAP/'selected-raw.npz')and r['original_capture_manifest']==str(CAP/'manifest.json'),'capture path binding')
  else:
   need(r['source']=='synthetic'and r['mode']in('one','capacity','lut-ties')and r['Qe']==[-9]*8 and r['Ke']==0 and r['Ve']==-14,'synthetic metadata')
   need(np.all(v==np.asarray([[(-32767 if(i+j)%2 else 32767)for j in range(128)]for i in range(n)])),'synthetic V extremes')
   if r['mode']in('one','capacity'):need(not q.any()and not k.any()and n==(1 if r['mode']=='one'else 1056),'zero-score boundary')
   else:need(n==6 and np.all(q[:,:4]==1)and not q[:,4:].any(),'tie query')
  dot=q@k.T;need(dot.min()>=-(1<<31)and dot.max()<1<<31,'QK32 range');scores=np.empty((8,n),np.int64)
  for h in range(8):
   shift=18-r['Qe'][h]-r['Ke'];need(-63<=shift<=63,'score shift')
   for j in range(n):
    product=int(dot[h,j])*94906266;need(-(1<<63)<=product<1<<63,'score S64');value=rne(product,shift);need(-(1<<31)<=value<1<<31,'score I32');scores[h,j]=value
    if j in(0,n//2,n-1):need(value==round(Fraction(product)*Fraction(2)**-shift),'score Fraction witness')
  if r['source']=='synthetic'and r['mode']=='lut-ties':need(np.array_equal(scores,np.tile([0,-16,-48,-65536,-65537,-32],(8,1))),'exact LUT/tie synthetic scores')
  distance=scores.max(axis=1)[:,None]-scores;eligible=distance<=65536;indices=distance>>5;rem=distance&31;indices+=(rem>16)|((rem==16)&((indices&1)!=0));indices=np.clip(indices,0,2048);exps=np.where(eligible,self.lut[indices],0);sums=exps.sum(axis=1,dtype=np.int64);p=np.empty((8,n),np.int64)
  for h in range(8):
   need(int(sums[h])>=1<<30 and int(sums[h])<=n*(1<<30),'sum bound')
   for j in range(n):p[h,j]=min(32767,round(Fraction(int(exps[h,j])<<15,int(sums[h]))))
  budget=32769+(n+1)//2;need(np.max(p.sum(axis=1))<=budget and budget*41024<1<<31,'normalized P guard');pv=p@v;need(pv.min()>=-(1<<31)and pv.max()<1<<31,'PV32 range')
  if r['source']=='real'and r['mode']=='full':
   f=OLD64/f"qwen25.prefix{r['prefix']}.l0.kv16.lut128.npz";need(str(f)==r['old64_reference']and sha(f)==self.old_artifacts[f.name]['sha256'],'old64 NPZ provenance')
   with np.load(f,allow_pickle=False)as z:
    idx=list(z['positions']).index(r['position'])
    for key,computed in [('QK32',dot),('scoreQ12',scores),('expQ30',exps),('P15',p)]:need(np.array_equal(computed,z[key][:,idx,:n]),'original64 valid-prefix '+key)
    need(np.array_equal(pv,z['PV32'][:,idx]),'original64 full PV')
  answer={'qk':dot.reshape(-1).tolist(),'score':scores.reshape(-1).tolist(),'exp':exps.reshape(-1).tolist(),'sum':sums.tolist(),'P':p.reshape(-1).tolist(),'out':pv.reshape(-1).tolist()};self.answers[name]=(r,answer,int(eligible.sum()));return self.answers[name]
def receive(run,inp,oracle,expected=None):
 m=json.loads((run/'manifest.json').read_text());artifacts(run,m);need(m['status']=='RTL_EXECUTED_NOT_RECEIVED','executed status');need(m['input_manifest_sha256']==sha(inp/'manifest.json'),'input manifest exact')
 binding=json.loads((ROOT/'binding.json').read_text())
 for n,h in binding['sources'].items():
  if n.startswith('project/rtl/')or n.endswith('/sim.cpp'):need(m['source']['sources'].get(n)==h,'actual RTL/driver byte binding '+n)
 records=[json.loads(line)for line in(run/'actual.jsonl').read_text().splitlines()];need(records,'actual rows')
 selected=[r['name']for r in oracle.rows]
 if m['pilot']==1:selected=[selected[i]for i in(0,7,8,39,76,78)]
 elif m['pilot']==2:selected=[selected[i]for i in(72,75,77)]
 need([r['name']for r in records]==selected,'exact preregistered rows/order')
 epochs=[];counts={'queries':len(records),'heads':8*len(records),'QK_values':0,'PV_values':0}
 for x in records:
  need(set(x)==KEYS,'exact result keyset');r,want,eligible=oracle.answer(x['name']);n=r['length'];integer(x['status'],0,0,'exact success int');need(x['role']==('pilot'if m['pilot']else'complete'),'role')
  for key in KEYS-{'name','role','qk','score','exp','sum','P','out'}:integer(x[key],0,(1<<64)-1,'exact uint '+key)
  need(x['length']==n,'length');epochs.append(x['epoch'])
  for key,values in want.items():need(type(x[key])is list and len(x[key])==len(values)and all(type(v)is int for v in x[key])and x[key]==values,'independent all-value '+key)
  tile=(n+15)//16;expected_counts={'macs':12288*n,'kloads':128*n,'vloads':128*n,'score_products':8*n,'mul_grants':8*n,'lut_reads':2*eligible,'divides':eligible,'transactions':256*n+2*eligible,'wire_beats':5*(256*n+2*eligible),'swrites':256*n+8*((n+3)//4)+8*((n+7)//8)+256*tile,'sreads':384*n+16*((n+3)//4)+128*((n+7)//8)+256*(tile-1)}
  for key,value in expected_counts.items():need(x[key]==value,'derived finite-port count '+key)
  need(x['cycles']>=x['macs']//8+128*x['divides'],'actual serial arithmetic lower bound')
  counts['QK_values']+=8*n;counts['PV_values']+=1024
 need(epochs==list(range(1,len(records)+1)),'same-core epochs')
 p=json.loads((run/'actual.jsonl.protocol.json').read_text());need(set(p)==set('schema accepted same_core_no_per_case_reset held_done latched_parameters canary_bytes fabric_high_water external_accepted'.split()),'protocol keys');need(p['schema']=='a102-protocol/1','protocol version')
 for k in('same_core_no_per_case_reset','held_done','latched_parameters'):need(p[k]is True,'exact protocol bool '+k)
 for k in('accepted','canary_bytes','fabric_high_water','external_accepted'):integer(p[k],0,(1<<32)-1,'protocol uint '+k)
 need(p['accepted']==len(records)and p['canary_bytes']==64 and p['fabric_high_water']==1 and p['external_accepted']==sum(r['transactions']for r in records),'actual protocol counts')
 return {'status':'PASS_COMPLETE_GQA_INTEGER_AND_FINITE_PORTS','counts':counts,'source':m['source'],'actual_sha256':sha(run/'actual.jsonl'),'protocol_sha256':sha(run/'actual.jsonl.protocol.json'),'input_manifest_sha256':sha(inp/'manifest.json'),'limits':['full and actual cached inputs distinct; cached final-prefix replay not append','not online, whole model quality, integrated M/A bank, SRAM/ROM macro or physical signoff']}
def main():
 p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);p.add_argument('--input',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--negative',action='store_true');a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
 binding=json.loads((ROOT/'binding.json').read_text())
 for n,h in binding['sources'].items():need(sha(ROOT/n)==h,'receiver frozen source '+n)
 try:
  oracle=Oracle(a.input);receipt=receive(a.run,a.input,oracle);receipt['receiver_source']=binding;neg=[]
  if a.negative:
   mutations=['out','qk','score','exp','sum','P','macs','sreads','lut_reads','status','missing','extra']
   for name in mutations:
    dest=a.out/('negative-'+name);dest.mkdir();m=json.loads((a.run/'manifest.json').read_text())
    for f in m['artifacts']:shutil.copyfile(a.run/f['path'],dest/f['path'])
    rows=[json.loads(x)for x in(dest/'actual.jsonl').read_text().splitlines()];x=rows[0]
    if name in('out','qk','score','exp','sum','P'):x[name][0]+=1
    elif name in('macs','sreads','lut_reads'):x[name]+=1
    elif name=='status':x['status']=True
    elif name=='missing':del x['score']
    else:x['unaccepted_extra']=0
    (dest/'actual.jsonl').write_text(''.join(json.dumps(v)+'\n'for v in rows),newline='\n')
    for f in m['artifacts']:f.update(bytes=(dest/f['path']).stat().st_size,sha256=sha(dest/f['path']))
    put(dest/'manifest.json',m)
    try:receive(dest,a.input,oracle)
    except (ValueError,KeyError,TypeError)as e:neg.append({'mutation':name,'rejected':True,'reason':str(e),'actual_sha256':sha(dest/'actual.jsonl'),'manifest_sha256':sha(dest/'manifest.json')})
    else:raise ValueError('tampered semantic file accepted '+name)
  receipt['semantic_file_negatives']=neg;put(a.out/'receipt.json',receipt);print(json.dumps({'status':receipt['status'],'counts':receipt['counts'],'negatives':len(neg)}))
 except Exception as e:put(a.out/'failure.json',{'status':'FAIL','error':str(e),'traceback':traceback.format_exc()});raise
if __name__=='__main__':main()
