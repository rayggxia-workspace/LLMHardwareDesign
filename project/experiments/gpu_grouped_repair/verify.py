"""Read back a candidate's hashes, exact integer samples and representative metrics."""
import argparse
import importlib.util
import json
from pathlib import Path
import torch

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('qwen_repair_audit_shared',HERE.parent/'gpu_model_repair/run.py')
common=importlib.util.module_from_spec(spec);spec.loader.exec_module(common)

def main():
    p=argparse.ArgumentParser();p.add_argument('candidate',type=Path);p.add_argument('--reference',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True);a=p.parse_args();assert not a.out.exists()
    checks={}
    for root in (a.candidate,a.reference):
        index=json.loads((root/'artifact-index.json').read_text(encoding='utf-8'))
        for name,info in index.items():
            assert (root/name).stat().st_size==info['bytes'] and common.sha(root/name)==info['sha256'],(root,name)
        checks[root.name+'_hashes']=len(index)
    sp=a.candidate/'integer-samples.pt'
    if sp.exists():
        samples=torch.load(sp,weights_only=True)
        for name,s in samples.items():assert torch.equal(s['A'].long()@s['B'].long(),s['accumulator'].long()),name
        checks['independent_int64_samples']=len(samples)
    result=json.loads((a.candidate/'results.json').read_text(encoding='utf-8'))
    ids=json.loads((a.reference/'inputs.json').read_text(encoding='utf-8'))
    regression=json.loads((a.reference/'regression-inputs.json').read_text(encoding='utf-8'))
    for split,tokens in [('test',ids['splits']['test'][0]['token_ids']),('regression',regression[0][0])]:
        cp=a.candidate/f'{split}-0.pt'
        if not cp.exists():continue
        c=torch.load(cp,weights_only=True);r=torch.load(a.reference/f'{split}-0.pt',weights_only=True)
        metrics=common.output_metrics(c,r,torch.tensor([tokens[1:]]))
        recorded=next(row for row in result['quality'] if row['split']==split and row['sample']==0)
        for key,value in metrics.items():
            if isinstance(value,bool):assert value==recorded[key]
            else:assert abs(value-recorded[key])<1e-6,(split,key,value,recorded[key])
        checks[split+'_representative_metrics_match']=True
    common.save(a.out,checks);print(json.dumps(checks))

if __name__=='__main__':main()
