"""Replay shipped selected real states without model weights or GPU."""
import argparse
import gzip
import json
from pathlib import Path
import torch
from run import compare, sha, save
from verify import recurrent


def main():
    p=argparse.ArgumentParser()
    p.add_argument('package',type=Path)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    index=json.loads((a.package/'package-index.json').read_text(encoding='utf-8'))
    for name,info in index.items():
        assert sha(a.package/name)==info['sha256'],name
    results=[]
    for kind in ('chunk','recurrent'):
        path=a.package/'selected-qwen35-layer0'/f'torch_{kind}_gated_delta_rule.pt.gz'
        with gzip.open(path,'rb') as f:
            payload=torch.load(f,weights_only=True,map_location='cpu')
        output,state=recurrent(payload)
        eo,es=compare(output,payload['output']),compare(state,payload['final_state'])
        _,bad=recurrent(payload,corrupt=True)
        negative=compare(bad,payload['final_state'])
        passed=eo['finite'] and es['finite'] and max(eo['relative_l2'],es['relative_l2'])<0.02
        if kind=='recurrent':passed=passed and negative['relative_l2']>=0.02
        results.append(dict(kind=kind,output=eo,state=es,wrong_initial_state=negative,passed=passed))
    save(a.out,{'package_files_sha_verified':len(index),'recurrent_replays':results,'pass':all(x['passed'] for x in results)})
    print(json.dumps(results))
    assert all(x['passed'] for x in results)


if __name__=='__main__':main()
