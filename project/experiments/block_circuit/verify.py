"""Independent exact math and result reception. Does not import compiler or baseline micro."""
import argparse,hashlib,json,math,copy
from pathlib import Path
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def need(v,s):
 if not v:raise ValueError(s)
def rne(n,d):
 if d==0:raise ZeroDivisionError()
 q,r=divmod(abs(n),d);return (-1 if n<0 else 1)*(q+int(2*r>d or(2*r==d and q%2)))
def wrap(n,w,signed=True):
 n%=1<<w
 return n-(1<<w)if signed and n>=1<<(w-1)else n
def scalar(v):
 op=v['op'];a=int(v['a']);b=int(v['b']);s=int(v['shift']);valid=True
 if op.startswith('mul_'):o={'value':a*b}
 elif op in('add_s64','sub_s64','add_u128'):
  w=128 if op=='add_u128'else 64;sg=op!='add_u128';n=a-b if op=='sub_s64'else a+b;valid=(-(1<<(w-1))<=n<(1<<(w-1)))if sg else(0<=n<1<<w);o={'value':wrap(n,w,sg)}
 elif op=='cmp_s64':o={'less':int(a<b),'equal':int(a==b)}
 elif op=='max_s64':o={'value':max(a,b)}
 elif op=='abs_s64':o={'value':abs(a)}
 elif op=='signextend_s16_i64':o={'value':a}
 elif op.startswith('shl_')or op=='align_s32_i64':
  w=64 if op=='align_s32_i64'else 128;sg=op!='shl_u128';n=a<<s;valid=(-(1<<(w-1))<=n<(1<<(w-1)))if sg else(0<=n<1<<w);o={'value':wrap(n,w,sg)}
 elif op.startswith('rne_')or op=='div_rne_s128_u64_i32':
  den=(1<<s)if op.startswith('rne_')else b
  if den==0:return {'valid':0}
  n=rne(a,den);valid=-(1<<31)<=n<1<<31;o={'value':n}
 elif op=='udiv_u128':
  if b==0:return {'valid':0}
  q,r=divmod(a,b);o={'quotient':q,'remainder':r}
 elif op=='isqrt_u128':o={'value':math.isqrt(a)}
 else:raise ValueError('registered scalar operation')
 o['valid']=int(valid);return o
def expected(v):
 k=v['kind']
 if k=='primitive':return scalar(v)
 if k=='ROM':return {'word':v['expected_word']}
 if k=='rq_chain':
  p=v['expected'];return {'value':rne(p['a']*p['b'],1<<p['raw_shift'])}
 if k=='merge8_chain':
  p=v['expected'];m=rne(sum(x*g for x,g in zip(p['down'],p['gates'])),1<<15);s=rne(m*230687,1<<20);result={'moe':m,'scaled':s,'joined':s+p['residual']}
  if p['original']is not None:need(result==p['original'],'actual original Granite full8/residual code')
  return result
 if k=='norm8_chain':
  p=v['expected'];den=math.isqrt((sum(x*x for x in p['x'])//p['H']+p['epsilon_q24'])<<40)
  return {'out'+str(i):rne((x*g)<<12,den)for i,(x,g)in enumerate(zip(p['x'],p['gamma']))}
 return {}
def check(vectors,rows):
 need(len(rows)==len(vectors),'all declared RTL cases executed');byname={r['name']:r for r in rows};need(len(byname)==len(rows),'unique received case')
 groups={};total={k:0 for k in('cycles','actions','fetch_lines','frame_read_lines','frame_write_lines','rom_requests','link_transactions','wire_beats')}
 for i,v in enumerate(vectors):
  r=byname[v['name']];need(r['status']==v['expected_status'],'actual RTL error/guard status '+v['name']);need(r['tag']==100+i,'completion tag')
  f=bytes.fromhex(r['frame']);need(len(f)==512,'finite published frame')
  need(r['wire_beats']==5*r['link_transactions'],'all request/response serialized beats')
  need(r['caller_setup_write_lines']==32 and r['caller_result_read_lines']==32,'explicit caller setup/extract, not free IO')
  if v['expected_status']==0:
   want=expected(v)
   for key,value in want.items():
    field=v['outputs'][key];encoded=bytes(f[j]for j in field['refs']);actual=int.from_bytes(encoded,'little',signed=field['signed']);need(actual==value,'independent numeric result '+v['name']+'.'+key+': '+str(actual)+' != '+str(value))
   if v['kind']=='primitive'and v.get('source_expected')is not None:need(want.get('value')==int(v['source_expected']),'original source code')
  # No all-eight SIMD discount; these are measured single-context hardware cycles.
  need(r['observed_active_edges']>=r['cycles'] and r['observed_active_edges']<=r['cycles']+3,'hardware cycles versus observed edges')
  for key in total:total[key]+=r[key]
  groups[v['kind']]=groups.get(v['kind'],0)+1
 return {'cases':len(rows),'groups':groups,'totals':total,'caller_IO_per_case':{'setup_full128bit_writes':32,'result_full128bit_reads':32},'eight_lane_parallel_throughput':'not implemented; one context chooses one of8physical lanes'}
def main():
 p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True);p.add_argument('--run',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--negative',action='store_true');p.add_argument('--limit',type=int);a=p.parse_args()
 need(not a.out.exists(),'new receipt only');im=json.loads((a.input/'manifest.json').read_text());rm=json.loads((a.run/'manifest.json').read_text())
 for root,m in((a.input,im),(a.run,rm)):
  for d in m['artifacts']:need(sha(root/d['path'])==d['sha256']and(root/d['path']).stat().st_size==d['bytes'],'actual artifact SHA')
 need(rm['status']=='RTL_EXECUTED','actual successful simulation');need(rm['input_manifest_sha256']==sha(a.input/'manifest.json'),'input bound to exact simulation')
 vectors=json.loads((a.input/'vectors.json').read_text());rows=[json.loads(x)for x in(a.run/'actual.jsonl').read_text().splitlines()];vectors=vectors[:a.limit] if a.limit is not None else vectors;result=check(vectors,rows)
 negatives=[]
 if a.negative:
  bad=copy.deepcopy(rows);v=vectors[0];r=bad[0];f=bytearray.fromhex(r['frame']);f[v['outputs']['value']['refs'][0]]^=1;r['frame']=f.hex()
  # Serialize the actual altered output, recompute its SHA, then invoke semantic check.
  path=a.out.with_name(a.out.stem+'-negative-numeric.jsonl');path.write_text(''.join(json.dumps(x)+'\n'for x in bad),encoding='utf-8');mutated=[json.loads(x)for x in path.read_text().splitlines()]
  try:check(vectors,mutated)
  except ValueError as e:negatives.append({'kind':'actual_numeric_rewrite','sha256':sha(path),'status':'REJECTED_AFTER_REHASH','reason':str(e)})
  else:raise ValueError('numeric semantic negative accepted')
 result.update(schema='block-circuit-independent80-v1',status='PASS_RTL_NUMERIC_PROTOCOL' if a.limit is None else 'PASS_PARTIAL_RTL_NUMERIC_PROTOCOL',source=rm['source'],input_manifest_sha256=sha(a.input/'manifest.json'),run_manifest_sha256=sha(a.run/'manifest.json'),mode=rm['mode'],stall=rm['stall'],semantic_negatives=negatives,limits=['Cycle measurements for this actual serialized RTL and external memory response model only; not entire LLM or process timing.','Program deployment and caller setup/result IO are separate explicit costs; no free control memory.','Generic synthesis/behavioral memories do not establish SRAM/ROM macro, STA or physical area/power.'])
 a.out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(result['status'],result['cases'])
if __name__=='__main__':main()
