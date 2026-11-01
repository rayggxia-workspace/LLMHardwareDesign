#!/bin/bash
#SBATCH --job-name=yzl-sc153-audit
#SBATCH --partition=c64
#SBATCH --nodelist=node1
#SBATCH --cpus-per-task=4
#SBATCH --time=00:30:00
set -euo pipefail
ROOT=/public/home/yuzelu/project-circuit/LLMHardwareDesign/systemc-llm-issue153
python3 - "$ROOT" <<'PY'
import pathlib,sys,json,hashlib,concurrent.futures,struct,subprocess,time
root=pathlib.Path(sys.argv[1]);started=time.time()
def sha(p):
    h=hashlib.sha256()
    with p.open('rb')as f:
        while True:
            block=f.read(16*1024*1024)
            if not block:break
            h.update(block)
    return dict(bytes=p.stat().st_size,sha256=h.hexdigest())
def audit(model):
    cp=root/(model+'-r8');run=root/('run-'+model+'-r9')
    export=json.loads((cp/'export_receipt.json').read_text());receipt=json.loads((run/'systemc_receipt.json').read_text());validation=json.loads((run/'validation.json').read_text())
    assert len(receipt['inputs'])==3 and len(receipt['generated'])==3 and len(validation['steps'])==3
    assert len(export['prompt_ids'])==1 and export['prompt']=='Hello'
    pref=json.loads((root/'continuation-r8/prefetch-source-hashes.json').read_text())
    earlier={row['path']:row for files in pref['files']for row in files}
    for row in export['source_files']:assert row==earlier[row['path']]
    files=[cp/name for name in ('weights.bin','weights.index','metadata.txt','prompt.txt','export_receipt.json','reference_hidden.bin','reference_logits.bin')]
    files += [run/name for name in ('systemc_hidden.bin','systemc_logits.bin','systemc_receipt.json','validation.json','run-inputs.sha256')]
    hashes={str(p):sha(p)for p in files}
    assert hashes[str(cp/'weights.bin')]['sha256']==export['weights_sha256']
    for p,h in validation['hashes'].items():assert hashes[p]['sha256']==h
    cfg=export['config'];expected=3*(cfg['num_hidden_layers']+1)
    def read_count(p,size):
        raw=p.read_bytes();offset=0;count=0
        while offset<len(raw):
            exp,n=struct.unpack_from('<iI',raw,offset);assert n==size
            offset+=8+n*2;count+=1
        assert offset==len(raw);return count
    assert read_count(run/'systemc_hidden.bin',cfg['hidden_size'])==expected
    assert read_count(run/'systemc_logits.bin',cfg['vocab_size'])==3
    log=(root/'logs'/('run-'+model+'-r9.log')).read_text()
    assert len([line for line in log.splitlines()if line.startswith('LAYER ')])==3*cfg['num_hidden_layers']
    assert receipt['transactions']['M']>0 and receipt['transactions']['S']>0 and receipt['transactions']['T']>0
    assert (receipt['transactions']['R']>0)==(model in ('qwen35','falcon'))
    return dict(model=model,scope='real complete TEXT checkpoint;3token short input; not model-quality acceptance',
                layers=cfg['num_hidden_layers'],vocab=cfg['vocab_size'],actual_layer_executions=3*cfg['num_hidden_layers'],
                hidden_records=expected,files=hashes,top1_equal=sum(s['top1_equal']for s in validation['steps']),
                logits_cosines=[s['logits']['cosine']for s in validation['steps']],generated=receipt['generated'],
                source_hashes_match_independent_readonly_prefetch=True)
with concurrent.futures.ThreadPoolExecutor(max_workers=4)as pool:models=list(pool.map(audit,('phi','gemma','qwen35','falcon')))
files={str(p):sha(p)for p in [root/'systemc-src-r9.tar.gz',root/'build-r9/llm_bench',root/'continuation-r8/prefetch-source-hashes.json']}
result=dict(scope='same-input complete text execution and actual file audit; numerical discrepancies remain explicit',
            models=models,files=files,seconds=time.time()-started,
            slurm=subprocess.check_output(['sacct','-j94515,94516,94518,94519,94520','-n','-X','-o','JobID,State,ExitCode,Elapsed,NodeList'],universal_newlines=True))
with (root/'continuation-r8/final-audit-r9.json').open('x')as f:json.dump(result,f,indent=2)
print(json.dumps({m['model']:dict(top1=m['top1_equal'],cosines=m['logits_cosines'])for m in models}),flush=True)
PY
