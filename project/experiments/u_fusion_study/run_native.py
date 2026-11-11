"""Server runner for matched production-S16 U stored/direct pair measurements."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shlex
import subprocess
import time

from prepare_native import render

HERE=Path(__file__).resolve().parent
VERILATOR=Path('/public/home/yuzelu/opt/eda/verilator-5-042-repro02/bin/verilator')
BANK=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-155/bank-views-011/generation/bank/s_sram_256x128_freepdk45.v')
BANK_SHA='6c1c1ca9d183ab7c4c74df056c9730cf352d165301546126e29b644a45ef9de7'
SMOKE_SHA='c5f0328e0bb13d9c074212aeb0ddad165b19b0c7cf0374b3cb6964f50ddf28b7'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def expand(text):
    sources=[]
    for token in shlex.split(text):
        match=re.fullmatch(r'([^{}]*)\{([^{}]+)\}([^{}]*)',token)
        if match:sources.extend(match[1]+x+match[3] for x in match[2].split(','))
        elif '{' in token or '}' in token:raise ValueError('unsupported source expansion')
        else:sources.append(token)
    return sources


def check_log(text):
    expression=r'NATIVE_FUSION_MEASURE direct=(\d+) tiles=(\d+) delay=(\d+) cycles=(\d+) S_reads=(\d+) S_writes=(\d+) N_commands=(\d+) E_commands=(\d+) direct_beats=(\d+) result=1049'
    records=[]
    for match in re.finditer(expression,text):
        row=dict(zip(('direct','tiles','delay','cycles','S_reads','S_writes','N_commands','E_commands','direct_beats'),map(int,match.groups())))
        n=row['tiles'];direct=row['direct']
        if row['S_reads']!=(3 if direct else 4)*n or row['S_writes']!=(1 if direct else 2)*n:
            raise ValueError('S transaction receipt mismatch')
        if row['N_commands']!=n or row['E_commands']!=n or row['direct_beats']!=(n if direct else 0) or row['cycles']<=0:
            raise ValueError('engine/transfer/cycle receipt mismatch')
        records.append(row)
    if len(records)!=8 or {(r['direct'],r['tiles'],r['delay']) for r in records}!={(d,t,s) for d in (0,1) for t in (1,16) for s in (0,4)}:
        raise ValueError('missing/duplicate matched cases')
    for marker in ('NATIVE_FUSION_CANCEL_PASS N_error_status=9 disabled_status=5 output_unchanged=1',
                   'NATIVE_FUSION_RESET_PASS held_producer_cancelled=1 no_stale_output=1',
                   'NATIVE_FUSION_PASS routes=2 tile_counts=1,16 handoff_delays=0,4 no_engine_replication=1'):
        if marker not in text:raise ValueError('missing functional receipt '+marker)
    comparisons=[]
    for tiles in (1,16):
        for delay in (0,4):
            old=next(r for r in records if (r['direct'],r['tiles'],r['delay'])==(0,tiles,delay))
            new=next(r for r in records if (r['direct'],r['tiles'],r['delay'])==(1,tiles,delay))
            comparisons.append(dict(tiles=tiles,handoff_delay=delay,stored_cycles=old['cycles'],direct_cycles=new['cycles'],
                saved_cycles=old['cycles']-new['cycles'],speedup=old['cycles']/new['cycles'],
                saved_S_payload_bytes=(old['S_reads']+old['S_writes']-new['S_reads']-new['S_writes'])*16))
    return dict(passed=True,cases=records,comparisons=comparisons,
                scope='single existing N/E pair; repeated tiles remain serialized by native pair control; no max(N,E) or token/s claim')


def main():
    p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True);p.add_argument('--workers',type=int,default=4)
    p.add_argument('--manifest',type=Path,required=True)
    a=p.parse_args();a.repo=a.repo.resolve();a.out=a.out.resolve();a.out.mkdir(parents=True,exist_ok=False)
    report=dict(passed=False,scope='unchanged production S16 RTL, fair RMS->ADD S/direct comparison; no S32 model/physical/whole-LLM qualification',
                versions={'python':platform.python_version()},commands=[])
    def execute(command,name):
        command=list(map(str,command));before=time.monotonic()
        run=subprocess.run(command,cwd=a.out,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
        log=a.out/name;log.write_bytes(run.stdout)
        record=dict(command=command,exit_code=run.returncode,elapsed_seconds=time.monotonic()-before,log=name,log_sha256=sha(log))
        report['commands'].append(record)
        if run.returncode:raise RuntimeError(str(command)+' exit '+str(run.returncode)+' '+run.stdout.decode(errors='replace')[-3500:])
        return run.stdout.decode(errors='replace')
    try:
        if not 1<=a.workers<=int(os.environ.get('SLURM_CPUS_PER_TASK','0')):raise ValueError('requires Slurm CPU allocation')
        if sha(BANK)!=BANK_SHA:raise ValueError('SRAM bank identity drift')
        smoke=a.repo/'project/experiments/pu_leaf_base/smoke.sh'
        if sha(smoke)!=SMOKE_SHA:raise ValueError('U smoke source identity drift')
        text=smoke.read_text(encoding='utf-8')
        common=re.search(r'common=\((.*?)\)\s*bank=',text,re.S)
        branch=re.search(r'3\) top=tb_pu_u_group\s*src=\((.*?)\);;',text,re.S)
        if not common or not branch:raise ValueError('U smoke source anchors changed')
        sources=expand(common[1])+expand(branch[1])
        if len(sources)!=13:raise ValueError('unexpected U source list '+str(sources))
        headers=set()
        for source in sources:
            for header in re.findall(r'`include\s+"([^"]+)"',(a.repo/source).read_text(encoding='utf-8')):
                resolved=a.repo/'project/rtl/block_v2'/header
                if not resolved.is_file():raise ValueError('missing header '+header)
                headers.add(str(resolved.relative_to(a.repo)))
        report['source_sha256']={s:sha(a.repo/s) for s in sources+sorted(headers)+['project/experiments/pu_leaf_base/smoke.sh']}
        report['study_sha256']={x.name:sha(x) for x in HERE.iterdir() if x.is_file() and x.suffix in ('.py','.sv','.json')}
        report['bank']=dict(path=str(BANK),sha256=BANK_SHA)
        report['verilator_binary_sha256']=sha(VERILATOR)
        report['versions']['verilator']=execute([VERILATOR,'--version'],'verilator-version.log').strip()
        report['versions']['gcc']=execute(['g++','--version'],'gcc-version.log').splitlines()[0]
        meta=a.manifest.resolve()
        provenance=json.loads(meta.read_text(encoding='utf-8'))
        commit=provenance.get('source_commit','')
        if not isinstance(commit,str) or not re.fullmatch('[0-9a-f]{40}',commit):
            raise ValueError('explicit manifest lacks a real source_commit')
        report['source_commit']=commit
        report['deployment_manifest']=dict(path=str(meta),sha256=sha(meta))
        report['bench']=render(a.repo,a.out/'prepared')
        obj=a.out/'obj'
        # Existing unchanged production RTL retains the exact smoke warning policy.
        execute([VERILATOR,'--binary','--timing','--assert','--timescale','1ns/1ps','-Wno-fatal',
                 '--x-initial','unique','--x-assign','unique','-j',a.workers,
                 '-I'+str(a.repo/'project/rtl/block_v2'),'--top-module','tb_fusion_native','--Mdir',obj,
                 a.out/'prepared/bench.sv',*[a.repo/s for s in sources],BANK],'native-build.log')
        cases=[]
        for mode,seed in ((1,143),(2,143),(2,144)):
            output=execute([obj/'Vtb_fusion_native',f'+verilator+rand+reset+{mode}',f'+verilator+seed+{seed}'],f'native-{mode}-{seed}.log')
            cases.append(dict(reset_mode=mode,seed=seed,checks=check_log(output)))
        report['runs']=cases;report['passed']=True
    except Exception as error:
        report['error']=type(error).__name__+': '+str(error);raise
    finally:
        report['output_sha256']={str(x.relative_to(a.out)):sha(x) for x in a.out.rglob('*')
            if x.is_file() and x.name!='result.json' and 'obj' not in x.relative_to(a.out).parts and x.suffix in ('.sv','.json','.log')}
        (a.out/'result.json').write_bytes((json.dumps(report,indent=2)+'\n').encode())
        print(json.dumps(dict(passed=report['passed'],result=str(a.out/'result.json'),error=report.get('error'))),flush=True)


if __name__=='__main__':main()
