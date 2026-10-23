"""Task-local packaging, no weights or large full validation tensors in Git."""
from pathlib import Path
import json, zipfile, hashlib, csv, gzip, shutil, statistics
ROOT=Path(__file__).resolve().parents[3]
scratch=Path('D:/Data/llm-gpu32')
out=ROOT/'project/experiments/gpu_model_evidence/results/issue-32'
out.mkdir(parents=True,exist_ok=True)
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(8<<20),b''):h.update(b)
    return h.hexdigest()
def save(p,d):
    p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
summary=[];timings=[];inventory=[]
for run in sorted((scratch/'runs').iterdir()):
    if not run.is_dir():continue
    rpath=run/'results.json'
    if rpath.exists():
        r=json.loads(rpath.read_text(encoding='utf-8'))
        if r['status']=='running' or not (run/'source-at-end.json').exists():continue
        row={k:r.get(k,[]) for k in ('status','correctness','quality','state_sensitivity','failures')}
        for k in ('continuation','sensitivity','test_aggregate','regression_aggregate','peak_allocated_bytes'):
            if k in r:row[k]=r[k]
        row.update(run=run.name,long_comparisons=[])
        for case in r.get('performance',[]):
            for s in case['samples']:
                eligible=run.name in ('qwen35-fp16-bounded-02','qwen25-fp16-bounded-01',
                    'qwen35-fp16-efficient-02','qwen25-fp16-efficient-01','qwen35-fp16-efficient-8192-01')
                timings.append({'run':run.name,'performance_eligible':eligible,'prefix':case['prefix'],'chunk':case['chunk'],**{k:v for k,v in s.items() if k not in ['cache','vs_one_shot','comparison_unavailable']}})
            sample=next(x for x in case['samples'] if x['repeat']==0)
            row['long_comparisons'].append({'prefix':case['prefix'],'chunk':case['chunk'],'comparison':sample.get('vs_one_shot'),'cache':sample['cache'],'median_total_s':statistics.median(x['total_s'] for x in case['samples'] if not x['warmup'])})
        summary.append(row)
    with zipfile.ZipFile(out/(run.name+'-metadata.zip'),'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in run.rglob('*'):
            if not p.is_file():continue
            inventory.append({'run':run.name,'file':str(p.relative_to(run)),'local_path':str(p),'bytes':p.stat().st_size,'sha256':sha(p)})
            if p.suffix in ('.json','.csv','.jsonl'):z.write(p,p.relative_to(run))
save(out/'summary.json',summary)
save(out/'local-artifacts.json',{'shared_storage':'Full traces/weights retained task-locally; shared storage pending approval. Selected layer0 raw states are in this package.','artifacts':inventory})
with (out/'all-timing-samples.csv').open('w',newline='') as f:
    fields=sorted(set().union(*(r.keys() for r in timings)))
    w=csv.DictWriter(f,fields);w.writeheader();w.writerows(timings)
save(out/'model-manifests.json',{n:json.loads((scratch/'models'/n/'model-manifest.json').read_text()) for n in ['qwen35','qwen25']})
with zipfile.ZipFile(out/'environment-and-audits.zip','w',zipfile.ZIP_DEFLATED) as z:
    for p in (scratch/'receipts').iterdir():
        if p.name in ['environment-before-cuda.json','environment-cuda.json','requirements-lock.txt','protocol-cuda.log','qwen35-long-wddm-samples.jsonl'] or p.name.endswith('-audit.json') or p.name.endswith('-readback.json'):
            z.write(p,p.name)
raw=out/'selected-qwen35-layer0';raw.mkdir(exist_ok=True)
for name in ['torch_chunk_gated_delta_rule.pt','torch_recurrent_gated_delta_rule.pt','delta-parameters.pt','preconv-qkv.pt','selected-cache.pt']:
    src=scratch/'runs/qwen35-fp16-bounded-02'/name
    if (raw/(name+'.gz')).exists():continue
    with src.open('rb') as f,gzip.open(raw/(name+'.gz'),'wb',compresslevel=6) as g:shutil.copyfileobj(f,g)
save(out/'package-index.json',{str(p.relative_to(out)):{'bytes':p.stat().st_size,'sha256':sha(p)} for p in out.rglob('*') if p.is_file() and p.name!='package-index.json'})
print('packaged',len(summary),'runs',len(timings),'samples',sum(p.stat().st_size for p in out.rglob('*') if p.is_file())/2**20,'MiB')
