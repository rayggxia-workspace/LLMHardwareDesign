#!/bin/bash
#SBATCH --job-name=yzl-sc153-audit
#SBATCH --partition=c64
#SBATCH --nodelist=node1
#SBATCH --cpus-per-task=6
#SBATCH --time=00:30:00
set -euo pipefail
ROOT=/public/home/yuzelu/project-circuit/LLMHardwareDesign/systemc-llm-issue153
REV=${1:-r13}
python3 - "$ROOT" "$REV" <<'PY'
import pathlib,sys,json,hashlib,concurrent.futures,struct,subprocess,time
root=pathlib.Path(sys.argv[1]);rev=sys.argv[2];started=time.time()
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for block in iter(lambda:f.read(16*1024*1024),b''):h.update(block)
    return dict(bytes=p.stat().st_size,sha256=h.hexdigest())
def audit(model):
    cp=root/({'qwen3':'qwen3-r2','qwen25':'qwen25-r2','granite':'granite-r1'}.get(model,model+'-r8'))
    run=root/('run-'+model+'-'+rev)
    export=json.loads((cp/'export_receipt.json').read_text());receipt=json.loads((run/'systemc_receipt.json').read_text());validation=json.loads((run/'validation.json').read_text())
    steps=len(export['reference_inputs']);assert len(receipt['inputs'])==steps and len(receipt['generated'])==3 and len(validation['steps'])==steps
    pref=json.loads((root/'continuation-r8/prefetch-source-hashes.json').read_text())
    earlier={row['path']:row for files in pref['files']for row in files}
    if model in ('phi','gemma','qwen35','falcon'):
        for row in export['source_files']:assert row==earlier[row['path']]
    files=[cp/name for name in ('weights.bin','weights.index','metadata.txt','prompt.txt','export_receipt.json','reference_hidden.bin','reference_logits.bin')]
    files += [run/name for name in ('systemc_hidden.bin','systemc_logits.bin','systemc_receipt.json','validation.json','run-inputs.sha256')]
    hashes={str(p):sha(p)for p in files}
    assert hashes[str(cp/'weights.bin')]['sha256']==export['weights_sha256']
    for p,h in validation['hashes'].items():assert hashes[p]['sha256']==h
    cfg=export['config'];expected=steps*(cfg['num_hidden_layers']+1)
    def read_count(p,size):
        raw=p.read_bytes();offset=0;count=0
        while offset<len(raw):
            exp,n=struct.unpack_from('<iI',raw,offset);assert n==size
            offset+=8+n*2;count+=1
        assert offset==len(raw);return count
    assert read_count(run/'systemc_hidden.bin',cfg['hidden_size'])==expected
    assert read_count(run/'systemc_logits.bin',cfg['vocab_size'])==steps
    log=(root/'logs'/('run-'+model+'-'+rev+'.log')).read_text()
    assert len([line for line in log.splitlines()if line.startswith('LAYER ')])==steps*cfg['num_hidden_layers']
    assert all(receipt['transactions'][m]>0 for m in ('M','N','E','G','S','T'))
    assert (receipt['transactions']['R']>0)==(model in ('qwen35','falcon'))
    return dict(model=model,scope='complete real TEXT checkpoint; short input functional evidence, not model-quality acceptance',
                layers=cfg['num_hidden_layers'],vocab=cfg['vocab_size'],steps=steps,actual_layer_executions=steps*cfg['num_hidden_layers'],
                hidden_records=expected,files=hashes,top1_equal=sum(s['top1_equal']for s in validation['steps']),
                logits_cosines=[s['logits']['cosine']for s in validation['steps']],generated=receipt['generated'],
                original_sources_rechecked_by_independent_prefetch=model in ('phi','gemma','qwen35','falcon'))
with concurrent.futures.ThreadPoolExecutor(max_workers=6)as pool:models=list(pool.map(audit,('phi','gemma','qwen35','falcon','qwen3','qwen25','granite')))
files={str(p):sha(p)for p in [root/('systemc-src-'+rev+'.tar.gz'),root/('build-'+rev)/'llm_bench',root/'continuation-r8/prefetch-source-hashes.json']}
result=dict(scope='complete text execution and actual file audit; precision limits retained',models=models,files=files,seconds=time.time()-started,
            slurm=subprocess.check_output(['sacct','-j94515,94518,94519,94520,94521,94522','-n','-X','-o','JobID,State,ExitCode,Elapsed,NodeList'],universal_newlines=True))
with (root/'continuation-r8'/('final-audit-'+rev+'.json')).open('x')as f:json.dump(result,f,indent=2)
print(json.dumps({m['model']:dict(top1=m['top1_equal'],steps=m['steps'],cosines=m['logits_cosines'])for m in models}),flush=True)
PY
