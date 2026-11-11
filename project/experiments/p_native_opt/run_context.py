"""Server entry point for isolated native M tests. This file does not submit jobs."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import time

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('native_context_generate',
    HERE/('generate_m_context.py' if (HERE/'generate_m_context.py').exists() else 'generate.py'))
generator=importlib.util.module_from_spec(spec);spec.loader.exec_module(generator)


def audit_case(row, contexts):
    routes=row['routes']
    assert row['contexts']==contexts and len(routes)==3
    assert routes[0]['A_handshakes']==routes[1]['A_handshakes']
    assert routes[1]['A_handshakes']==routes[2]['A_handshakes']*contexts
    assert len({r['B_handshakes'] for r in routes})==1
    assert len({r['B_logical_bytes'] for r in routes})==1
    assert routes[1]['commands']==routes[2]['commands']
    for r in routes:
        assert r['A_wire_bytes']==16*r['A_handshakes']
        assert r['B_wire_bytes']==64*r['B_handshakes']
        assert r['A_logical_bytes']==(16 if row['Awide'] else 8)*r['A_handshakes']
        assert r['B_logical_bytes']==64*r['B_handshakes']
    return True


def run(repo,out,verilator,cpus=4):
    repo,out=Path(repo).resolve(),Path(out).resolve()
    assert 1<=cpus<=4
    affinity=sorted(os.sched_getaffinity(0)) if hasattr(os,'sched_getaffinity') else []
    if affinity:
        assert cpus<=len(affinity)
    out.mkdir(parents=True,exist_ok=False)
    receipt=dict(passed=False,issue=247,started_unix=time.time(),runs=[],builds=[],
                 cpus=cpus,cpu_affinity=affinity,physical_qualified=False,
                 scope='Native M operand/command handshakes; no SRAM, DDR, or clock qualification')
    def call(command,log):
        with (out/log).open('w',encoding='utf-8') as f:
            result=subprocess.run([str(c) for c in command],cwd=repo,stdout=f,stderr=subprocess.STDOUT,
                                  env=dict(os.environ,OMP_NUM_THREADS=str(cpus),OPENBLAS_NUM_THREADS='1'))
        assert result.returncode==0,(log,result.returncode)
    try:
        generated=out/'generated';receipt['generation']=generator.generate(repo,generated)
        formal=repo/'project/rtl/block_v2/block_v2_m_context.sv'
        assert formal.read_bytes()==(generated/'block_v2_m_context.sv').read_bytes(), 'formal/generated context RTL drift'
        receipt['formal_context_sha256']=generator.sha(formal)
        receipt['verilator_version']=subprocess.check_output([verilator,'--version'],text=True).strip()
        jobs=[('baseline','block_v2_m','test_m.cpp',None),
              ('legacy_candidate','block_v2_m_context','test_legacy_candidate.cpp',8)]
        jobs += [(f'contexts{n}','block_v2_m_context','test_context.cpp',n) for n in (1,2,8)]
        prior_legacy={}
        for label,top,cpp,n in jobs:
            parameters=[] if n is None else [f'-GCONTEXTS={n}']
            rtl=generated/(top+'.sv');obj=out/('obj_'+label)
            call([verilator,'--lint-only','-Wall','--top-module',top,*parameters,rtl],label+'-lint.log')
            # Original C++ tests retain their exact original flags. The new code
            # and its extracted original helpers are compiled with strict warnings.
            flags='-std=c++17 -O1'
            if label.startswith('contexts'):
                flags+=f' -Wall -Wextra -Werror -DTEST_CONTEXTS={n}'
            command=[verilator,'--cc','--exe','--build','-j',str(cpus),'--top-module',top,*parameters,
                     '--Mdir',obj,'--x-initial','unique','--x-assign','unique','-CFLAGS',flags,rtl,generated/cpp]
            call(command,label+'-build.log');receipt['builds'].append(dict(label=label,command=list(map(str,command))))
            for mode,seed in ((1,247),(2,247),(2,248)):
                log=f'{label}-{mode}-{seed}.jsonl'
                call([obj/('V'+top),f'+verilator+rand+reset+{mode}',f'+verilator+seed+{seed}'],log)
                rows=[json.loads(s) for s in (out/log).read_text().splitlines() if s.startswith('{')]
                final=rows[-1];assert final['passed']
                if label=='baseline':
                    prior_legacy[(mode,seed)]=final
                elif label=='legacy_candidate':
                    assert final==prior_legacy[(mode,seed)],'legacy numeric/cycle regression'
                else:
                    cases=[r for r in rows if r.get('type')=='case'];assert len(cases)==44
                    assert final['contexts']==n and final['cases']==44
                    for row in cases:audit_case(row,n)
                receipt['runs'].append(dict(label=label,mode=mode,seed=seed,result=final,
                                            log=log,sha256=generator.sha(out/log)))
        # Source-lock and payload-accounting rejection must exercise the real entry.
        wrong=dict(generator.FROZEN);wrong[generator.RTL]='0'*64
        try:generator.verify_sources(repo,wrong)
        except ValueError:receipt['source_drift_rejected']=True
        else:raise AssertionError('source drift accepted')
        sample=next(r for r in rows if r.get('type')=='case')
        changed=json.loads(json.dumps(sample));changed['routes'][2]['A_handshakes']+=1
        try:audit_case(changed,8)
        except AssertionError:receipt['traffic_drift_rejected']=True
        else:raise AssertionError('traffic drift accepted')
        receipt['passed']=True
    finally:
        receipt['finished_unix']=time.time()
        receipt['outputs_sha256']={p.name:generator.sha(p) for p in sorted(out.iterdir()) if p.is_file()}
        (out/'result.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    return receipt


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True);p.add_argument('--cpus',type=int,default=4)
    p.add_argument('--verilator',default='/public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator')
    a=p.parse_args();print(json.dumps(run(a.repo,a.out,a.verilator,a.cpus)))
