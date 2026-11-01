import pathlib,subprocess,tarfile,io,shutil,json,struct,math
base=pathlib.Path('.local/continuation/structural-r35');base.mkdir(exist_ok=False)
families=('phi3','gemma3_text','qwen3_5_text','falcon_h1')
for m in families:shutil.copytree(pathlib.Path('.local/continuation/structural-r10')/(m+'-cp'),base/(m+'-cp'))
code='''import pathlib,tarfile,sys
r=pathlib.Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/systemc-llm-issue153/structural-r10')
with tarfile.open(fileobj=sys.stdout.buffer,mode='w|gz',dereference=True) as t:
 for m in ('phi3','gemma3_text','qwen3_5_text','falcon_h1'):
  for n in ('reference_logits.bin','reference_hidden.bin'):t.add(str(r/(m+'-cp')/n),arcname=m+'-cp/'+n)
'''
r=subprocess.run(['ssh','yuzelu@10.129.166.172','python3 -'],input=code.encode(),capture_output=True,check=True)
with tarfile.open(fileobj=io.BytesIO(r.stdout),mode='r:gz')as t:
 for p in t.getmembers():assert p.isfile()and'..'not in p.name; (base/p.name).write_bytes(t.extractfile(p).read())
p=base/'falcon_h1-cp/metadata.txt';s=p.read_text();md=dict(l.split()for l in s.splitlines());md['attention_multiplier']=str(1/math.sqrt(int(md['head_dim'])));p.write_text('\n'.join(k+' '+v for k,v in md.items())+'\n')
lines=['set -euo pipefail','cd /mnt/d/Data/电路实验/LLMHardwareDesign-worktrees/issue-153-systemc-llm','export LLM_PRECISE_ADAPTER=1 LLM_BLOCK_SCALES=1 LLM_ACCURATE_SILU=1']
for m in families:
 out=base/(m+'-run');out.mkdir();lines.append('.systemc-build-r8/llm_bench '+str(base/(m+'-cp')).replace('\\','/')+' '+str(out).replace('\\','/')+' > '+str(base/(m+'.log')).replace('\\','/')+' 2>&1')
subprocess.run(['wsl','-d','Ubuntu-18.04','--','bash','-s'],input=('\n'.join(lines)+'\n').encode(),check=True)
def decode(p):
 raw=p.read_bytes();o=0;out=[]
 while o<len(raw):
  e,n=struct.unpack_from('<iI',raw,o);o+=8
  es=struct.unpack_from('<'+'i'*n,raw,o)if e==-2147483648 else[e]*n
  if e==-2147483648:o+=4*n
  vals=struct.unpack_from('<'+'h'*n,raw,o);o+=2*n
  out.append([math.ldexp(v,e)for v,e in zip(vals,es)])
 return out
def metric(a,b):
 aa=sum(x*x for x in a);bb=sum(x*x for x in b)
 return {'relative_l2':math.sqrt(sum((x-y)**2 for x,y in zip(a,b))/bb),'cosine':sum(x*y for x,y in zip(a,b))/math.sqrt(aa*bb)}
results={}
for m in families:
 cp=base/(m+'-cp');out=base/(m+'-run');cfg=json.loads((cp/'export_receipt.json').read_text())['config'];ls=decode(out/'systemc_logits.bin');hs=decode(out/'systemc_hidden.bin')
 report={}
 for key,actual,size in [('logits',ls,cfg['vocab_size']),('hidden',hs,cfg['hidden_size'])]:
  raw=(cp/('reference_'+key+'.bin')).read_bytes();ref=struct.unpack('<'+'f'*(len(raw)//4),raw)
  expected=[ref[i:i+size]for i in range(0,len(ref),size)]
  assert len(actual)==len(expected)
  metrics=[metric(x,y)for x,y in zip(actual,expected)]
  report[key]={'max_relative_l2':max(x['relative_l2']for x in metrics),'min_cosine':min(x['cosine']for x in metrics)}
  if key=='logits':report['top1']=sum(max(range(size),key=lambda i:x[i])==max(range(size),key=lambda i:y[i])for x,y in zip(actual,expected))
 report['scope']='synthetic two-layer fixture, not pretrained model acceptance'
 results[m]=report
print(json.dumps(results,indent=2))
(base/'local-fixture-assessment.json').write_text(json.dumps(results,indent=2)+'\n')
