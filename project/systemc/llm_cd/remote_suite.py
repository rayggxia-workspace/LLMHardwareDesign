"""Seven actual checkpoint runs, dynamic six-worker refill, frozen numerical gates."""
from pathlib import Path
import concurrent.futures,subprocess,os,json,hashlib,re,time
ROOT=Path(os.environ['CD_EXPERIMENT_ROOT']);OLD=ROOT.parent
SOURCE=ROOT/'source';TOOLS=SOURCE/'project/systemc/llm/tools'
PY='/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python'
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for c in iter(lambda:f.read(8*1024*1024),b''):h.update(c)
 return h.hexdigest()
def model(name):
 run=ROOT/('run-'+name);run.mkdir();start=time.time()
 cp=OLD/('sequence-'+name+('-f14' if name in ('gemma','falcon') else '-f7' if name=='qwen25' else '-f4'))
 env=dict(os.environ,OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1',HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',LLM_PRECISE_ADAPTER='1',LLM_BLOCK_SCALES='1',LLM_ACCURATE_SILU='1',LLM_LINK='1',LLM_LINK_WIDTH_BYTES='64',LLM_LINK_QUEUE_PACKETS='1',LLM_FLOW_DIR=str(run))
 for key in ('LLM_LINK_CORRUPT','LLM_LINK_DROP_RESPONSE','LLM_FIRST_LAYER_ONLY','LLM_TRACE_LAYER','LLM_NORM_FUSED','LLM_SSM_BLOCK_SCALES'):env.pop(key,None)
 commands=[[ROOT/'experiment/build/llm_cd_bench',cp,run],['python3',TOOLS/'analyze_flow.py',run],[PY,TOOLS/'validate_inference.py',cp,run],['python3',TOOLS/'assess_numerics.py',run/'validation.json','--out',run/'numerical-gates.json']]
 receipt=dict(passed=False,checkpoint=str(cp),started_epoch=start,commands=[],binary_sha256=sha(ROOT/'experiment/build/llm_cd_bench'))
 try:
  for i,cmd in enumerate(commands):
   with (run/(str(i)+'.log')).open('w') as f:q=subprocess.run(list(map(str,cmd)),env=env,stdout=f,stderr=subprocess.STDOUT)
   receipt['commands'].append(dict(argv=list(map(str,cmd)),returncode=q.returncode));assert q.returncode==0,(name,i,q.returncode)
  gate=json.loads((run/'numerical-gates.json').read_text());assert gate['accepted'] and gate['steps']==9 and gate['top1_equal']==9
  log=(run/'0.log').read_text();counts=re.findall(r'CD_EXECUTED windows=(\d+) words=(\d+) bursts=(\d+) C_submitted=(\d+) C_completed=(\d+)',log)
  assert len(counts)==1 and int(counts[0][0])>0 and counts[0][3]==counts[0][4]
  receipt.update(passed=True,numerical_gate=gate,cd_counts=counts[0])
 except Exception as e:receipt['error']=str(e)
 finally:
  receipt['seconds']=time.time()-start
  receipt['checkpoint_inputs']={p.name:dict(bytes=p.stat().st_size,sha256=sha(p)) for p in cp.iterdir()if p.is_file() and p.name in ('weights.bin','weights.index','metadata.txt','export_receipt.json','weights.scales','parameters.scales','reference_hidden.npy','reference_logits.npy')}
  receipt['outputs']={p.name:dict(bytes=p.stat().st_size,sha256=sha(p)) for p in run.iterdir()if p.is_file()}
  (run/'execution.json').write_text(json.dumps(receipt,indent=2)+'\n')
 return name,receipt
results={}
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
 futures=[pool.submit(model,n)for n in ('phi','gemma','qwen35','falcon','qwen3','qwen25','granite')]
 for f in concurrent.futures.as_completed(futures):
  name,r=f.result();results[name]=r;print(name,r['passed'],r.get('error'),flush=True)
  (ROOT/'suite-progress.json').write_text(json.dumps(results,indent=2)+'\n')
passed=len(results)==7 and all(r['passed'] for r in results.values())
(ROOT/'suite-final.json').write_text(json.dumps(dict(passed=passed,models=results),indent=2)+'\n')
raise SystemExit(0 if passed else 1)
