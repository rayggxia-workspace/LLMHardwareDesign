"""Read back hashes, fixed inputs, independent selected recurrent update and bad-state control."""
import argparse
import json
from pathlib import Path
import torch
from run import sha, save, compare


def recurrent(payload, corrupt=False):
    q,k,v=[payload[n].float().transpose(1,2) for n in ('query','key','value')]
    if payload['use_qk_l2norm_in_kernel']:
        q=q/torch.sqrt((q*q).sum(-1,keepdim=True)+1e-6)
        k=k/torch.sqrt((k*k).sum(-1,keepdim=True)+1e-6)
    q=q/(q.shape[-1]**0.5)
    g,b=[payload[n].float().transpose(1,2) for n in ('g','beta')]
    initial=payload['initial_state']
    state=torch.zeros((*k.shape[:2],k.shape[-1],v.shape[-1])) if initial is None else initial.float().clone()
    if corrupt: state+=0.125
    outputs=[]
    for i in range(q.shape[2]):
        state=state*g[:,:,i].exp()[...,None,None]
        prediction=torch.einsum('bhk,bhkv->bhv',k[:,:,i],state)
        correction=(v[:,:,i]-prediction)*b[:,:,i,None]
        state=state+torch.einsum('bhk,bhv->bhkv',k[:,:,i],correction)
        outputs.append(torch.einsum('bhk,bhkv->bhv',q[:,:,i],state))
    return torch.stack(outputs,2).transpose(1,2).to(payload['output'].dtype),state


def main():
    p=argparse.ArgumentParser();p.add_argument('run',type=Path);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();idx=json.loads((a.run/'artifact-index.json').read_text())
    checked=[]
    for n,info in idx.items():
        path=a.run/n
        assert path.stat().st_size==info['bytes'] and sha(path)==info['sha256'],n
        checked.append(n)
    res=json.loads((a.run/'results.json').read_text())
    result={'hashes_verified':checked,'run_status':res['status'],'recurrent':[]}
    integer_path=a.run/'integer-kernel-samples.pt'
    if integer_path.exists():
        result['integer_samples']=[]
        for n,payload in torch.load(integer_path,weights_only=True).items():
            # INT64 scalar-product expansion independent of the CUDA INT8 kernel.
            acc=(payload['A'].long()[:,:,None]*payload['B'].long()[None,:,:]).sum(1)
            result['integer_samples'].append({'module':n,'pass':bool(torch.equal(acc,payload['accumulator'].long())),
                                               'shape':list(acc.shape)})
    for name in ('torch_chunk_gated_delta_rule','torch_recurrent_gated_delta_rule'):
        path=a.run/(name+'.pt')
        if path.exists():
            payload=torch.load(path,weights_only=True,map_location='cpu')
            out,state=recurrent(payload)
            eo,es=compare(out,payload['output']),compare(state,payload['final_state'])
            badout,badstate=recurrent(payload,corrupt=True)
            bad=compare(badstate,payload['final_state'])
            # Native chunk and sequential recurrent accumulation order can differ.
            ok=eo['finite'] and es['finite'] and eo['relative_l2']<0.02 and es['relative_l2']<0.02
            detected=bad['relative_l2']>=0.02
            result['recurrent'].append({'file':name,'output_error':eo,'state_error':es,
                'pass':ok,'corrupt_initial_state_error':bad,'negative_detected':detected})
    result['pass']=res['status'].startswith('completed') and all(x['pass'] for x in result['recurrent'])
    result['pass']=result['pass'] and all(x['pass'] for x in result.get('integer_samples',[]))
    # The cached single-token call must reject the wrong recurrent state. Prefill may forget corruption.
    cached=[x for x in result['recurrent'] if x['file']=='torch_recurrent_gated_delta_rule']
    result['pass']=result['pass'] and all(x['negative_detected'] for x in cached)
    save(a.out,result);print(json.dumps(result))
    if not result['pass']: raise SystemExit(1)


if __name__=='__main__': main()
