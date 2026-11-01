#!/bin/bash
#SBATCH --job-name=yzl-sc153-audit
#SBATCH --partition=c64
#SBATCH --nodelist=node1
#SBATCH --cpus-per-task=6
#SBATCH --time=00:30:00
set -euo pipefail
ROOT=/public/home/yuzelu/project-circuit/LLMHardwareDesign/systemc-llm-issue153
REV=${1:-r17}
python3 - "$ROOT" "$REV" "${2:-}" "${3:-phi,gemma,qwen35,falcon,qwen3,qwen25,granite}" <<'PY'
import pathlib,sys,json,hashlib,concurrent.futures,struct,subprocess,time
root=pathlib.Path(sys.argv[1]);rev=sys.argv[2];started=time.time()
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for block in iter(lambda:f.read(16*1024*1024),b''):h.update(block)
    return dict(bytes=p.stat().st_size,sha256=h.hexdigest())
def audit(model):
    run=root/('run-'+model+'-'+rev)
    receipt=json.loads((run/'systemc_receipt.json').read_text());validation=json.loads((run/'validation.json').read_text())
    weight_paths=[pathlib.Path(p)for p in validation['hashes']if p.endswith('/weights.bin')]
    assert len(weight_paths)==1
    cp=weight_paths[0].parent
    assert len(cp.relative_to(root).parts)==1
    export=json.loads((cp/'export_receipt.json').read_text())
    steps=len(export['reference_inputs']);assert len(receipt['inputs'])==steps and len(receipt['generated'])==3 and len(validation['steps'])==steps
    pref=json.loads((root/'continuation-r8/prefetch-source-hashes.json').read_text())
    earlier={row['path']:row for files in pref['files']for row in files}
    if model in ('phi','gemma','qwen35','falcon'):
        for row in export['source_files']:assert row==earlier[row['path']]
    files=[cp/name for name in ('weights.bin','weights.index','metadata.txt','prompt.txt','export_receipt.json','reference_hidden.bin','reference_logits.bin')]
    if (cp/'weights.scales').exists():
        files.append(cp/'weights.scales')
        assert sha(cp/'weights.scales')['sha256']==export['weight_scales_sha256']
    files += [run/name for name in ('systemc_hidden.bin','systemc_logits.bin','systemc_receipt.json','validation.json','run-inputs.sha256')]
    files += sorted(run.glob('stage-*.bin'))
    files += sorted(run.glob('*diagnostic.json'))
    files += [root/'logs'/('run-'+model+'-'+rev+'.log')]
    hashes={str(p):sha(p)for p in files}
    assert hashes[str(cp/'weights.bin')]['sha256']==export['weights_sha256']
    for p,h in validation['hashes'].items():assert hashes[p]['sha256']==h
    cfg=export['config'];expected=steps*(cfg['num_hidden_layers']+1)
    def read_count(p,size):
        raw=p.read_bytes();offset=0;count=0
        while offset<len(raw):
            exp,n=struct.unpack_from('<iI',raw,offset);assert n==size
            offset+=8+n*2+(n*4 if exp==-2147483648 else 0);count+=1
        assert offset==len(raw);return count
    assert read_count(run/'systemc_hidden.bin',cfg['hidden_size'])==expected
    assert read_count(run/'systemc_logits.bin',cfg['vocab_size'])==steps
    log=(root/'logs'/('run-'+model+'-'+rev+'.log')).read_text()
    assert len([line for line in log.splitlines()if line.startswith('LAYER ')])==steps*cfg['num_hidden_layers']
    assert all(receipt['transactions'][m]>0 for m in ('M','N','E','S','T'))
    # Accurate SiLU is composed from M/N/E commands and legitimately bypasses G.
    # GEMMA GELU and the recurrent families still exercise their G operations.
    g_required=(receipt.get('silu_adapter')!='range-reduced-N-exp, Newton reciprocal, M/E'
                or model in ('gemma','qwen35','falcon'))
    if g_required:assert receipt['transactions']['G']>0
    assert (receipt['transactions']['R']>0)==(model in ('qwen35','falcon'))
    return dict(model=model,scope='complete real TEXT checkpoint; short input functional evidence, not model-quality acceptance',
                layers=cfg['num_hidden_layers'],vocab=cfg['vocab_size'],steps=steps,actual_layer_executions=steps*cfg['num_hidden_layers'],
                hidden_records=expected,files=hashes,top1_equal=sum(s['top1_equal']for s in validation['steps']),
                logits_cosines=[s['logits']['cosine']for s in validation['steps']],generated=receipt['generated'],
                original_sources_rechecked_by_independent_prefetch=model in ('phi','gemma','qwen35','falcon'))
with concurrent.futures.ThreadPoolExecutor(max_workers=6)as pool:models=list(pool.map(audit,sys.argv[4].split(',')))
files={str(p):sha(p)for p in [root/('systemc-src-'+rev+'.tar.gz'),root/('build-'+rev)/'llm_bench',root/'continuation-r8/prefetch-source-hashes.json']}
result=dict(scope='complete text execution and actual file audit; precision limits retained',models=models,files=files,seconds=time.time()-started,
            slurm=subprocess.check_output(['sacct','-j'+sys.argv[3],'-n','-X','-o','JobID,State,ExitCode,Elapsed,NodeList'],universal_newlines=True) if sys.argv[3] else 'execution job IDs not supplied')
with (root/'continuation-r8'/('final-audit-'+rev+'.json')).open('x')as f:json.dump(result,f,indent=2)
print(json.dumps({m['model']:dict(top1=m['top1_equal'],steps=m['steps'],cosines=m['logits_cosines'])for m in models}),flush=True)
PY
