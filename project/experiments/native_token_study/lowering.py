"""Strict frozen-trace inventory and explicit admission gate; not a compiler."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path


def read_trace(path):
    lines=Path(path).read_text(encoding='utf-8').splitlines();nt,no,tokens=map(int,lines[0].split())
    tensors=[]
    for line in lines[1:nt+1]:
        tid,count,bits,initial=map(int,line.split());assert tid==len(tensors)
        assert bits in (8,16,32,64);tensors.append(dict(elements=count,bits=bits,initial=bool(initial)))
    ops=[]
    for line in lines[nt+1:]:
        p=line.split();assert len(p)>=10
        out=int(p[0]);inputs=list(map(int,p[10:]));assert len(inputs)==int(p[9])
        assert all(0<=v<out for v in inputs)
        ops.append(dict(out=out,kind=p[1],elements=int(p[2]),rows=int(p[3]),cols=int(p[4]),
                        k=int(p[5]),batches=int(p[6]),shift=int(p[7]),layout=int(p[8]),inputs=inputs))
    assert len(ops)==no
    return tensors,ops,tokens


def analyse(path):
    path=Path(path);tensors,ops,tokens=read_trace(path);dot=[o for o in ops if o['kind']=='Dot']
    shapes=Counter();s32_calls=s32_occurrences=static_eligible=0;logical_MACs=0
    for o in dot:
        assert len(o['inputs'])==2 and o['k']>0 and o['rows']>0 and o['cols']>0 and o['batches']>0
        widths=[tensors[t]['bits'] for t in o['inputs']]
        s32_calls+=any(b==32 for b in widths);s32_occurrences+=sum(b==32 for b in widths)
        shapes[(o['rows'],o['cols'],o['k'],o['batches'],o['layout'],*widths,o['shift'])]+=1
        logical_MACs+=o['rows']*o['cols']*o['k']*o['batches']
        static_eligible+=o['layout']==0 and o['rows']==1 and o['k']*(3 if widths[0]==32 else 1)<=65535
    s32_tensors=sum(t['bits']==32 for t in tensors)
    reasons=['full_graph_instruction_and_DDR_bridge_compiler_not_implemented']
    if s32_tensors:reasons.append('lossless_S32_digit_adapter_and_S96_merge_are_conditional_unimplemented_hardware')
    if any(o['kind'] not in ('Dot','Constant') for o in ops):reasons.append('U_graph_retains_frozen_S32_candidate_services')
    return dict(trace_name=path.name,trace_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        tensors=len(tensors),ops=len(ops),tokens=tokens,S32_tensor_count=s32_tensors,
        tensor_width_counts=dict(Counter(t['bits'] for t in tensors)),kind_counts=dict(Counter(o['kind'] for o in ops)),
        all_Dot_calls=len(dot),S32_Dot_calls=s32_calls,S32_Dot_input_occurrences=s32_occurrences,
        non_Dot_candidate_ops=len(ops)-len(dot),original_useful_MACs=logical_MACs,
        static_context_eligible_calls=static_eligible,max_K=max((o['k'] for o in dot),default=0),
        native_admitted=False,native_rejection_reasons=reasons,
        static_shapes=[dict(rows=k[0],cols=k[1],K=k[2],batches=k[3],layout=k[4],A_bits=k[5],B_trace_bits=k[6],
                            output_shift=k[7],calls=v) for k,v in sorted(shapes.items())],
        qualification='Conditional timing lowering inventory only; tensor payloads, per-tensor numeric scales and full native instruction stream are absent')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--trace',type=Path,required=True)
    p.add_argument('--out',type=Path);p.add_argument('--require-native',action='store_true');a=p.parse_args()
    r=analyse(a.trace);text=json.dumps(r,indent=2)+'\n'
    if a.out:
        a.out.parent.mkdir(parents=True,exist_ok=True)
        with a.out.open('x',encoding='utf-8') as f:f.write(text)
    print(text,end='')
    if a.require_native and not r['native_admitted']:raise SystemExit(3)
