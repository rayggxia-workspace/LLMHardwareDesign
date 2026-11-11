"""Slurm-only runner for isolated single-N/single-E finite-FIFO overlap."""
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

from prepare_overlap import render

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


def check_log(text,depth):
    if depth not in (1,2,4):raise ValueError('unsupported depth')
    names=('depth','overlap','tiles','delay','cycles','S_reads','S_writes','N_commands','E_commands','E_beats','FIFO_pushes','FIFO_pops','max_inflight','verified_slots')
    expression=(r'OVERLAP_MEASURE depth=(\d+) overlap=(\d+) tiles=(\d+) delay=(\d+) cycles=(\d+) '
                r'S_reads=(\d+) S_writes=(\d+) N_commands=(\d+) E_commands=(\d+) E_beats=(\d+) '
                r'FIFO_pushes=(\d+) FIFO_pops=(\d+) max_inflight=(\d+) verified_slots=(\d+)')
    rows=[]
    for match in re.finditer(expression,text):
        row=dict(zip(names,map(int,match.groups())));n=row['tiles'];overlap=row['overlap']
        if row['depth']!=depth or overlap not in (0,1) or row['cycles']<=0:
            raise ValueError('depth/route/cycle receipt')
        if row['S_reads']!=3*n or row['S_writes']!=n or any(row[k]!=n for k in ('N_commands','E_commands','E_beats','verified_slots')):
            raise ValueError('transaction/numerical receipt')
        if row['FIFO_pushes']!=(n if overlap else 0) or row['FIFO_pops']!=(n if overlap else 0):
            raise ValueError('FIFO conservation receipt')
        if not 1<=row['max_inflight']<=min(n,depth+2) or (not overlap and row['max_inflight']!=1):
            raise ValueError('bounded inflight receipt')
        rows.append(row)
    expected={(o,t,d) for o in (0,1) for t in (1,16,32) for d in (0,4)}
    if len(rows)!=12 or {(r['overlap'],r['tiles'],r['delay']) for r in rows}!=expected:
        raise ValueError('missing/duplicate matched cases')
    full=re.findall(r'OVERLAP_FULL_PASS depth=(\d+) held_cycles=8 recovered_tiles=(\d+) max_inflight=(\d+)',text)
    if len(full)!=1 or tuple(map(int,full[0][:2]))!=(depth,depth+3) or not depth+1<=int(full[0][2])<=depth+2:
        raise ValueError('full/hold/recovery receipt')
    for marker in (
        f'OVERLAP_RESET_PASS depth={depth} held_producer_cancelled=1 empty_after_reset=1 fresh_tile_verified=1',
        f'OVERLAP_PASS depth={depth} routes=2 tile_counts=1,16,32 delays=0,4 one_N_one_E=1',
    ):
        if text.count(marker)!=1:raise ValueError('missing/duplicate functional receipt '+marker)
    comparisons=[]
    for tiles in (1,16,32):
        for delay in (0,4):
            old=next(r for r in rows if (r['overlap'],r['tiles'],r['delay'])==(0,tiles,delay))
            new=next(r for r in rows if (r['overlap'],r['tiles'],r['delay'])==(1,tiles,delay))
            comparisons.append(dict(tiles=tiles,handoff_delay=delay,serial_direct_cycles=old['cycles'],
                fifo_overlap_cycles=new['cycles'],saved_cycles=old['cycles']-new['cycles'],
                speedup=old['cycles']/new['cycles'],max_inflight=new['max_inflight'],
                S_transactions_identical=True))
    return dict(passed=True,depth=depth,cases=rows,comparisons=comparisons,
                scope='one unchanged production N/E/S; real finite tagged register FIFO and experimental scheduler; native S16 only')


def main():
    p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--workers',type=int,default=4);p.add_argument('--manifest',type=Path,required=True)
    a=p.parse_args();a.repo=a.repo.resolve();a.out=a.out.resolve();a.out.mkdir(parents=True,exist_ok=False)
    report=dict(passed=False,scope='isolated FIFO/scheduler candidate, unchanged S16 N/E/S; no production, S32, token/s, P&R or timing qualification',
                versions={'python':platform.python_version()},commands=[])
    def execute(command,name):
        command=list(map(str,command));before=time.monotonic()
        run=subprocess.run(command,cwd=a.out,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
        log=a.out/name;log.write_bytes(run.stdout)
        report['commands'].append(dict(command=command,exit_code=run.returncode,elapsed_seconds=time.monotonic()-before,
                                      log=name,log_sha256=sha(log)))
        if run.returncode:raise RuntimeError('command exit '+str(run.returncode)+' '+str(command)+' '+run.stdout.decode(errors='replace')[-3500:])
        return run.stdout.decode(errors='replace')
    try:
        if not 1<=a.workers<=min(4,int(os.environ.get('SLURM_CPUS_PER_TASK','0'))):raise ValueError('requires Slurm CPU allocation; workers <=4')
        manifest=a.manifest.resolve();meta=json.loads(manifest.read_text(encoding='utf-8'))
        commit=meta.get('source_commit','')
        if not isinstance(commit,str) or not re.fullmatch('[0-9a-f]{40}',commit):raise ValueError('explicit manifest lacks real source_commit')
        report['source_commit']=commit;report['deployment_manifest']=dict(path=str(manifest),sha256=sha(manifest))
        if sha(BANK)!=BANK_SHA:raise ValueError('SRAM bank identity drift')
        smoke=a.repo/'project/experiments/pu_leaf_base/smoke.sh'
        if sha(smoke)!=SMOKE_SHA:raise ValueError('U smoke identity drift')
        text=smoke.read_text(encoding='utf-8')
        common=re.search(r'common=\((.*?)\)\s*bank=',text,re.S)
        branch=re.search(r'3\) top=tb_pu_u_group\s*src=\((.*?)\);;',text,re.S)
        if not common or not branch:raise ValueError('U smoke anchors changed')
        sources=expand(common[1])+expand(branch[1])
        if len(sources)!=13:raise ValueError('unexpected U source list')
        headers=set()
        for source in sources:
            for header in re.findall(r'`include\s+"([^"]+)"',(a.repo/source).read_text(encoding='utf-8')):
                resolved=a.repo/'project/rtl/block_v2'/header
                if not resolved.is_file():raise ValueError('missing header '+header)
                headers.add(str(resolved.relative_to(a.repo)))
        report['source_sha256']={s:sha(a.repo/s) for s in sources+sorted(headers)+[
            'project/experiments/pu_leaf_base/smoke.sh','project/experiments/pu_leaf_base/tb_pu_u_group.sv']}
        report['study_sha256']={x:sha(HERE/x) for x in ('prepare_overlap.py','run_overlap.py','overlap_control.sv','overlap_parser_selftest.py')}
        report['bank']=dict(path=str(BANK),sha256=BANK_SHA);report['verilator_binary_sha256']=sha(VERILATOR)
        report['versions']['verilator']=execute([VERILATOR,'--version'],'verilator-version.log').strip()
        report['versions']['gcc']=execute(['g++','--version'],'gcc-version.log').splitlines()[0]
        report['bench']=render(a.repo,a.out/'prepared')
        # Candidate only: warnings are fatal. The unchanged production closure
        # below retains precisely its original smoke -Wno-fatal warning policy.
        for depth in (1,2,4):
            execute([VERILATOR,'--lint-only','--top-module','u_overlap_control',f'-GDEPTH={depth}',
                     HERE/'overlap_control.sv'],f'controller-lint-depth{depth}.log')
        runs=[]
        for depth in (1,2,4):
            obj=a.out/f'obj-depth{depth}'
            execute([VERILATOR,'--binary','--timing','--assert','--timescale','1ns/1ps','-Wno-fatal',
                     '--x-initial','unique','--x-assign','unique','-j',a.workers,
                     '-I'+str(a.repo/'project/rtl/block_v2'),'--top-module','tb_overlap_native',f'-GDEPTH={depth}',
                     '--Mdir',obj,a.out/'prepared/bench_overlap.sv',HERE/'overlap_control.sv',
                     *[a.repo/s for s in sources],BANK],f'overlap-build-depth{depth}.log')
            for mode,seed in ((1,143),(2,143),(2,144)):
                output=execute([obj/'Vtb_overlap_native',f'+verilator+rand+reset+{mode}',f'+verilator+seed+{seed}'],
                               f'overlap-depth{depth}-{mode}-{seed}.log')
                runs.append(dict(depth=depth,reset_mode=mode,seed=seed,checks=check_log(output,depth)))
        # An inactive experimental FIFO must not change the serial comparator.
        serial={}
        for run in runs:
            for row in run['checks']['cases']:
                if row['overlap']:continue
                key=(row['tiles'],row['delay'])
                if key in serial and serial[key]!=row['cycles']:raise ValueError('serial reference cycles changed across depth/seed')
                serial[key]=row['cycles']
        report['runs']=runs;report['passed']=True
    except Exception as error:
        report['error']=type(error).__name__+': '+str(error);raise
    finally:
        report['output_sha256']={str(x.relative_to(a.out)):sha(x) for x in a.out.rglob('*')
            if x.is_file() and x.name!='result.json' and not any(p.startswith('obj-') for p in x.relative_to(a.out).parts)
            and x.suffix in ('.sv','.json','.log')}
        (a.out/'result.json').write_bytes((json.dumps(report,indent=2)+'\n').encode())
        print(json.dumps(dict(passed=report['passed'],result=str(a.out/'result.json'),error=report.get('error'))),flush=True)


if __name__=='__main__':main()
