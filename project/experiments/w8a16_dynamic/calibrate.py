"""Measure full N8 layouts using the already-qualified unchanged M binary."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
from oracle import finish,partials
from check import pack


def main(args):
    assert os.environ.get('SLURM_JOB_ID')
    assert json.loads((args.proof/f'rtl-{args.seed}/result.json').read_text())['passed']
    provider=json.loads((args.proof/'m-provider-source.json').read_text())
    assert provider['commit']=='f08aefb93df071535f461da24b6829c5949bf5bf'
    witness=json.loads((args.proof/'checkpoint/checkpoint-vectors.json').read_text())
    qk=next(v for v in witness if v['role']=='QK');av=next(v for v in witness if v['role']=='AV')
    # Extending the B1/S2 witness to N8/K512 is a synthetic shape exercise,
    # not a real decode512 tensor or a new quality result.
    a=qk['A'];b=[row*4 for row in qk['B']]
    aa=(av['A']*256)[:512];bb=(av['B']*256)[:512]
    samples=[(a,b,24,0),(a,b,24,1),(aa,bb,24,1)]
    args.out.mkdir(parents=True,exist_ok=False);lines=[]
    for a,b,shift,major in samples:
        n=len(b[0]);lines.append(f'{len(a)} {n} {shift} {major}')
        lines.extend(format(x&0xffffffff,'x') for x in a)
        lines.extend(format(x&0xffffffff,'x') for row in b for x in row)
        lines.append(format(pack([finish(sum(x*row[c] for x,row in zip(a,b)),shift) for c in range(n)],32),'x'))
        lines.extend(format(pack(p['raw'],32),'x') for p in partials(a,b))
    vectors=args.out/'vectors.txt';vectors.write_text('\n'.join(lines)+'\n')
    binary=args.proof/f'rtl-{args.seed}/obj-product/Vtb_product'
    report=dict(passed=False,binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),
                M_provider=provider,proof=str(args.proof),vector_sha256=hashlib.sha256(vectors.read_bytes()).hexdigest(),runs=[])
    try:
        for initial in range(3):
            for ideal in (0,1):
                path=args.out/f'product-{initial}-{ideal}.log'
                with path.open('w') as log:
                    subprocess.run([str(binary),'+vectors='+str(vectors),'+ideal='+str(ideal),
                        '+verilator+seed+'+str(args.seed),'+verilator+rand+reset+'+str(initial)],
                        check=True,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT)
                text=path.read_text();assert 'PASS dynamic_product cases=3 partials=90 ' in text
                start={int(r):int(c) for c,r in re.findall(r'JOINT_PARTIAL_BEGIN cycle=(\d+) record=(\d+)',text)}
                raw={int(r):int(c) for c,r in re.findall(r'JOINT_RAW cycle=(\d+) record=(\d+)',text)}
                begin=[(int(c),int(v,16)) for c,v in re.findall(r'JOINT_LC cycle=(\d+) data=([0-9a-f]+)',text)]
                # Header length lets us skip payload words, not interpret a
                # payload's low bits as an opcode by coincidence.
                i=0;headers=[]
                while i<len(begin):
                    c,v=begin[i]
                    if (v>>16)&15==1:headers.append(c)
                    i+=(v>>20)&15
                rows=[dict(record=r,partial_begin=start[r],raw_cycle=c,begin_to_raw=c-h,
                           partial_to_raw=c-start[r]) for (r,c),h in zip(raw.items(),headers)]
                assert len(rows)==90
                report['runs'].append(dict(initial=initial,ideal=bool(ideal),log=path.name,
                    sha256=hashlib.sha256(path.read_bytes()).hexdigest(),record_costs=rows))
        report['passed']=True
    finally:(args.out/'result.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--proof',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True);p.add_argument('--seed',type=int,required=True)
    main(p.parse_args())
