"""Static byte microcode compiler. No runtime operand value becomes instruction bits."""
import argparse,hashlib,importlib.util,io,json,struct
from pathlib import Path
HERE=Path(__file__).resolve().parent
BASE=HERE.parent/'granite_ports'/'micro.py'
spec=importlib.util.spec_from_file_location('baseline_micro80',BASE);M=importlib.util.module_from_spec(spec);spec.loader.exec_module(M)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def put(p,v):Path(p).write_text(json.dumps(v,indent=2,sort_keys=True)+'\n',encoding='utf-8',newline='\n')
def operand(v):
 if v<0:
  if not 0<=-1-v<=255:raise ValueError('immediate')
  return 512+(-1-v)
 if v>=512:raise ValueError('address')
 return v
def byte(op,a=-1,b=-1,c=-1,dst=-1,hi=-1,check=False):
 return op|operand(a)<<4|operand(b)<<14|operand(c)<<24|(max(dst,0)<<34)|(max(hi,0)<<43)|(int(hi>=0)<<52)|(int(dst>=0)<<53)|(int(check)<<54)
def call(base,selector=-1,limit=0):return 12|operand(selector)<<4|base<<14|limit<<46
def template(op,shift=0,a=0,b=1):
 s=io.StringIO();result,profile=M.execute(op,a,b,shift,s,'template');instructions=[];fields={};outputs={};init={};started=False;h=hashlib.sha256()
 for line in s.getvalue().splitlines():
  t=line.split();u=t[:]
  if t[0]=='A':u=t[:7]
  elif t[0]=='I':u=t[:2]
  elif t[0]=='O':u=t[:4]
  elif t[0]in('B','E'):u=t[:1]
  h.update((' '.join(u)+'\n').encode())
  if t[0]=='M'and t[3]in('input_a','input_b','publish_valid'):fields[t[3]]=[int(t[1]),int(t[2])]
  elif t[0]=='I':
   if started:raise ValueError('no initialized intermediate after arithmetic')
   init[int(t[1])]=int(t[2])
  elif t[0]=='A':
   started=True;v=list(map(int,t[1:7]));instructions.append(byte(*v))
  elif t[0]=='O':outputs[t[1]]={'signed':bool(int(t[2])),'refs':list(map(int,t[3].split(',')))}
 if fields['publish_valid']!=[0,1]or profile['scratch_peak_bytes']>256:raise ValueError('leaf reserved-half capacity')
 permitted={0}
 for key in ('input_a','input_b'):
  if key in fields:off,n=fields[key];permitted.update(range(off,off+n))
 if set(init)!=permitted:raise ValueError('only original inputs initialized')
 return {'words':[byte(0,-2,dst=0),*instructions,14],'fields':fields,'outputs':outputs,'topology':h.hexdigest(),'actions':len(instructions)+1,'scratch':profile['scratch_peak_bytes']}
class Catalog:
 def __init__(self):self.words=[];self.tables={};self.templates={};self.wrappers={}
 def allocate(self,words):
  p=len(self.words);self.words.extend(words);return p
 def build(self):
  for op in M.OP_SPECS:
   n=64 if op=='align_s32_i64'else 128 if op.startswith('shl_')else 129 if op.startswith('rne_')else 1
   table=self.allocate([0]*n);self.tables[op]=(table,n)
   for shift in range(n):
    t=template(op,shift);self.templates[(op,shift)]=t;self.words[table+shift]=self.allocate(t['words'])
   t=self.templates[(op,0)];w=[]
   for key,src in [('input_a',256),('input_b',288)]:
    if key in t['fields']:
     dst,count=t['fields'][key];w += [byte(0,src+i,dst=dst+i)for i in range(count)]
   w +=[call(table,496,n-1),15];self.wrappers[op]=self.allocate(w)
  return self
 def invoke(self,out,op,a,b=None,shift=0,selector=None,guard=True):
  t=self.templates[(op,0)]
  for key,src in [('input_a',a),('input_b',b)]:
   if key in t['fields']:
    if src is None:raise ValueError('missing input '+op)
    dst,n=t['fields'][key];out += [byte(0,src+i,dst=dst+i)for i in range(n)]
  table,n=self.tables[op];out.append(call(table,selector if selector is not None else -1-shift,n-1))
  if guard:out.append(byte(11,0,check=True))
  return t['outputs']
 def save(self,out):
  if len(self.words)%2:self.words.append(15)
  data=b''.join(struct.pack('<Q',x)for x in self.words)
  if len(data)>32<<20:raise ValueError('bounded program deployment32MiB within EXT128MiB')
  (out/'program.bin').write_bytes(data)
  return {'words':len(self.words),'bytes':len(data),'sha256':sha(out/'program.bin'),'external_capacity_budget_bytes':134217728,'program_budget_bytes':33554432,'fetch_cache_bytes':16,'note':'not a free internal microcode ROM; all external instruction/table reads use actual RTL bridge'}
def encode_at(buf,offset,value,n,signed=True):buf[offset:offset+n]=int(value).to_bytes(n,'little',signed=signed)
def collect(primary,out,binding,granite=()):
 out.mkdir(parents=True,exist_ok=False);old=json.loads((primary/'manifest.json').read_text());entries={x['path']:x for x in old['artifacts']}
 if old['status']!='PASS_BYTE_CORE_AND_WIDE_MICROPROGRAM':raise ValueError('qualified original')
 for name in ('cases.json','rom.hex','rom.requests'):
  if sha(primary/name)!=entries[name]['sha256']:raise ValueError('input SHA '+name)
 if old['source']['micro_sha256']!=sha(BASE):raise ValueError('baseline exact source')
 records=json.loads((primary/'cases.json').read_text());C=Catalog().build();vectors=[]
 for i,r in enumerate(records):
  op=r['op'];original_shift=int(r['shift']);shift=original_shift if C.tables[op][1]>1 else 0;t=C.templates[(op,shift)];actual=template(op,original_shift,int(r['a']),int(r['b']))
  if actual['words']!=t['words']or actual['topology']!=r['topology_sha256']:raise ValueError('input-independent source topology '+r['case'])
  f=bytearray(512)
  for key,src,val in [('input_a',256,r['a']),('input_b',288,r['b'])]:
   if key in t['fields']:
    n=t['fields'][key][1];encode_at(f,src,int(val),n,not(op=='add_u128'or op=='udiv_u128'or op=='shl_u128'or op=='isqrt_u128'or(op=='mul_s32_u16'and key=='input_b')or(op=='div_rne_s128_u64_i32'and key=='input_b')))
  f[496]=shift
  vectors.append({'name':r['case'],'kind':'primitive','op':op,'a':r['a'],'b':r['b'],'shift':original_shift,'hardware_shift_selector':shift,'source':r['source'],'source_expected':r.get('source_expected'),'pc':C.wrappers[op],'lane':i%8,'expected_status':0,'input':f.hex(),'outputs':t['outputs'],'source_result':r['result']})
 # ROM words are read by RTL memory, not supplied as host-computed results.
 for i,line in enumerate((primary/'rom.requests').read_text().splitlines()):
  address,value=map(int,line.split());f=bytearray(512);f[256]=address&255;f[257]=address>>8
  pc=C.allocate([13|operand(256)<<4|operand(257)<<14|272<<34,15])
  vectors.append({'name':'rom'+str(i),'kind':'ROM','pc':pc,'lane':i%8,'expected_status':0,'input':f.hex(),'outputs':{'word':{'signed':False,'refs':list(range(272,276))}},'address':address,'expected_word':value})
 # Actual illegal program paths are executed and must produce stable error statuses.
 for name,words,expected in [('bad_reserved',[1<<63],2),('return_underflow',[14],3),('guard_reject',[byte(11,-1,check=True),15],7)]:
  pc=C.allocate(words);vectors.append({'name':name,'kind':'protocol_negative','pc':pc,'lane':0,'expected_status':expected,'input':bytes(512).hex(),'outputs':{}})
 f=bytearray(512);f[496]=129;vectors.append({'name':'shift129_reject','kind':'protocol_negative','pc':C.wrappers['rne_s64_i32'],'lane':0,'expected_status':4,'input':f.hex(),'outputs':{}})
 for name,address in [('rom_oob',32768)]:
  f=bytearray(512);f[256]=address&255;f[257]=address>>8;pc=C.allocate([13|operand(256)<<4|operand(257)<<14|272<<34,15]);vectors.append({'name':name,'kind':'protocol_negative','pc':pc,'lane':0,'expected_status':5,'input':f.hex(),'outputs':{}})
 table=C.allocate([0]);recursive=C.allocate([call(table),15]);C.words[table]=recursive
 vectors.append({'name':'stack_overflow','kind':'protocol_negative','pc':recursive,'lane':0,'expected_status':3,'input':bytes(512).hex(),'outputs':{}})
 vectors.append({'name':'pc_oob','kind':'protocol_negative','pc':0xffffffff,'lane':0,'expected_status':1,'input':bytes(512).hex(),'outputs':{}})
 chains(C,vectors,granite)
 program=C.save(out);put(out/'vectors.json',vectors)
 with(out/'vectors.tsv').open('x',encoding='ascii',newline='\n')as stream:
  for v in vectors:stream.write(f"{v['name']} {v['pc']} {v['lane']} {v['expected_status']} {v['input']}\n")
 (out/'rom.hex').write_bytes((primary/'rom.hex').read_bytes())
 put(out/'manifest.json',{'schema':'block-circuit-input80-v1','source':binding,'original_micro_manifest_sha256':sha(primary/'manifest.json'),'original_cases_sha256':sha(primary/'cases.json'),'baseline_micro_sha256':sha(BASE),'program':program,'vectors':len(vectors),'primitive_vectors':len(records),'actual_Granite_vectors':sum(isinstance(r['source'],dict)for r in records),'topology_data_independence_checked':len(records),'artifacts':[{'path':n,'bytes':(out/n).stat().st_size,'sha256':sha(out/n)}for n in('program.bin','vectors.json','vectors.tsv','rom.hex')]})
 print(json.dumps({'status':'COMPILED_NOT_RTL_EXECUTED','vectors':len(vectors),'program':program}))
def chains(C,vectors,granite=()):
 from graphs import add_chains
 add_chains(C,vectors,granite,byte,encode_at,operand)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--primary',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--binding',type=Path,required=True);p.add_argument('--granite',type=Path,action='append',default=[]);a=p.parse_args();collect(a.primary,a.out,json.loads(a.binding.read_text()),a.granite)
