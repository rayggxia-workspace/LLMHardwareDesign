"""Slurm runner: fixed real-1RW SRAM backend and production local_s_p tests."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import time

HERE=Path(__file__).resolve().parent
VERILATOR=Path('/public/home/yuzelu/opt/eda/verilator-5-042-repro02/bin/verilator')
BANK=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-155/bank-views-011/generation/bank/s_sram_256x128_freepdk45.v')
BANK_SHA='6c1c1ca9d183ab7c4c74df056c9730cf352d165301546126e29b644a45ef9de7'
SOURCES=['project/rtl/s_sram/block_feed_s16k_sram.sv',
         'project/rtl/s_sram/block_feed_s16k_bank_rw.sv',
         'project/rtl/s_sram/local_s_p.sv',
         'project/rtl/block_feed_v1/block_feed_loader.sv']


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def parse(text,kind,mode,reuse,hold=32):
    if kind=='backend':
        rows=re.findall(r'POPT_MEMORY_MEASURE bank_rw=(\d+) cycles=(\d+) narrow=64 wide=32 bank_operations=192 parallel_cycles=(\d+) max_n_wait=(\d+) max_w_wait=(\d+)',text)
        if len(rows)!=1:raise ValueError('missing/duplicate backend measurement')
        m,cycles,parallel,n_wait,w_wait=map(int,rows[0])
        if m!=mode or cycles<=0 or (mode and not parallel) or (not mode and parallel) or (mode and max(n_wait,w_wait)>6):
            raise ValueError('backend physical/fairness receipt')
        marker=f'POPT_MEMORY_PASS bank_rw={mode} scoreboards=2 snapshot=1 response_stability=1 reservation=1 fairness=1 reset=1'
        result=dict(kind=kind,bank_rw=mode,cycles=cycles,narrow_commands=64,wide_commands=32,
                    physical_bank_operations=192,parallel_physical_cycles=parallel,max_narrow_wait=n_wait,max_wide_wait=w_wait)
    else:
        rows=re.findall(r'POPT_LOCAL_MEASURE bank_rw=(\d+) reuse_a=(\d+) hold=(\d+) cycles=(\d+) narrow_writes=64 wide_reads=6 A_beats=16 B_beats=2 writes_while_load_owned=(\d+)',text)
        if len(rows)!=1:raise ValueError('missing/duplicate local measurement')
        m,r,h,cycles,owned=map(int,rows[0])
        if m!=mode or r!=reuse or h!=hold or hold not in (0,32) or cycles<=0 or (mode and not owned) or (not mode and owned):raise ValueError('local phase/concurrency/hold receipt')
        marker=f'POPT_LOCAL_PASS bank_rw={mode} reuse_a={reuse} hold={hold} load_range_guard=1 rows0_contract=1 feeder_scoreboard=1 done_ack=1 reset=1'
        bonly=(f'POPT_LOCAL_BONLY_PASS bank_rw={mode} reuse_a={reuse} hold={hold} shapes=16 boundaries=16 cross=14 '
               f'unaligned_a=16 unaligned_b=16 legal={32 if reuse else 0} rejected={46 if reuse else 78} A_beats=0 B_reads={120 if reuse else 0}')
        if text.count(bonly)!=1:raise ValueError('missing/duplicate B-only matrix receipt')
        result=dict(kind=kind,bank_rw=mode,reuse_a=reuse,hold_cycles=hold,cycles=cycles,narrow_writes=64,wide_reads=6,
                    A_beats=16,B_beats=2,writes_while_load_owned=owned,
                    bonly_functional=dict(shapes=16,boundaries=16,aligned_cross=14,unaligned_a=16,unaligned_b=16,
                                          legal=32 if reuse else 0,rejected=46 if reuse else 78,A_beats=0,B_reads=120 if reuse else 0))
    if text.count(marker)!=1:raise ValueError('missing/duplicate pass marker '+marker)
    return result


def main():
    p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--workers',type=int,default=4);p.add_argument('--manifest',type=Path,required=True)
    p.add_argument('--only',choices=('all','backend','local'),default='all')
    a=p.parse_args();a.repo=a.repo.resolve();a.out=a.out.resolve();a.out.mkdir(parents=True,exist_ok=False)
    report=dict(passed=False,scope='fixed 16KiB four real1RW macros; bank-mask partial wide gather and independent narrow access; no 1R1W/SRAM expansion/STA qualification',
                versions={'python':platform.python_version()},commands=[])
    def execute(command,name):
        command=list(map(str,command));before=time.monotonic()
        run=subprocess.run(command,cwd=a.out,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
        log=a.out/name;log.write_bytes(run.stdout)
        report['commands'].append(dict(command=command,exit_code=run.returncode,elapsed_seconds=time.monotonic()-before,log=name,log_sha256=sha(log)))
        if run.returncode:raise RuntimeError('command failed '+str(command)+' '+run.stdout.decode(errors='replace')[-3500:])
        return run.stdout.decode(errors='replace')
    try:
        if not 1<=a.workers<=min(4,int(os.environ.get('SLURM_CPUS_PER_TASK','0'))):raise ValueError('requires actual Slurm allocation, workers<=4')
        manifest=a.manifest.resolve();meta=json.loads(manifest.read_text(encoding='utf-8'));commit=meta.get('source_commit','')
        if not isinstance(commit,str) or not re.fullmatch('[0-9a-f]{40}',commit):raise ValueError('manifest needs actual 40hex source_commit')
        report['source_commit']=commit;report['deployment_manifest']=dict(path=str(manifest),sha256=sha(manifest))
        sources=SOURCES if a.only!='backend' else SOURCES[:2]
        for name in sources:
            if meta.get('code_sha256',{}).get(name)!=sha(a.repo/name):raise ValueError('source differs from deployment manifest '+name)
        if sha(BANK)!=BANK_SHA:raise ValueError('real SRAM bank SHA drift')
        report['source_sha256']={s:sha(a.repo/s) for s in sources}
        report['study_sha256']={x.name:sha(x) for x in HERE.iterdir() if x.is_file() and x.suffix in ('.py','.sv','.json')}
        report['bank']=dict(path=str(BANK),sha256=BANK_SHA);report['verilator_binary_sha256']=sha(VERILATOR)
        report['versions']['verilator']=execute([VERILATOR,'--version'],'verilator-version.log').strip()
        report['versions']['gcc']=execute(['g++','--version'],'gcc-version.log').splitlines()[0]
        execute([VERILATOR,'--lint-only','--timing','--timescale','1ns/1ps','--top-module','block_feed_s16k_bank_rw',
                 a.repo/SOURCES[1],BANK],'bank-rw-strict-lint.log')
        variants=[]
        if a.only!='local':variants.extend(('backend',m,0,0) for m in (0,1))
        if a.only!='backend':variants.extend(('local',m,r,h) for h in (0,32) for m,r in ((0,0),(1,0),(1,1)))
        runs=[]
        for kind,mode,reuse,hold in variants:
            top='tb_popt_memory' if kind=='backend' else 'tb_popt_local'
            bench=HERE/(top+'.sv');obj=a.out/f'obj-{kind}-{mode}-{reuse}-h{hold}'
            deps=SOURCES[:2] if kind=='backend' else SOURCES
            params=[f'-GBANK_RW={mode}']+([f'-GREUSE_A={reuse}',f'-GHOLD_CYCLES={hold}'] if kind=='local' else [])
            # The unchanged vendor/production closure retains its smoke warning
            # policy; the new backend is separately linted strictly above.
            execute([VERILATOR,'--binary','--timing','--assert','--timescale','1ns/1ps','-Wno-fatal',
                     '--x-initial','unique','--x-assign','unique','-j',a.workers,
                     '--top-module',top,*params,'--Mdir',obj,bench,*[a.repo/s for s in deps],BANK],
                    f'build-{kind}-{mode}-{reuse}-h{hold}.log')
            for reset_mode,seed in ((1,143),(2,143),(2,144)):
                log=f'run-{kind}-{mode}-{reuse}-h{hold}-{reset_mode}-{seed}.log'
                text=execute([obj/('V'+top),f'+verilator+rand+reset+{reset_mode}',f'+verilator+seed+{seed}'],log)
                runs.append(dict(reset_mode=reset_mode,seed=seed,checks=parse(text,kind,mode,reuse,hold)))
        local_comparisons=[]
        for hold in (0,32):
            base=[r for r in runs if r['checks']['kind']=='local' and r['checks']['bank_rw']==0 and r['checks']['hold_cycles']==hold]
            candidate=[r for r in runs if r['checks']['kind']=='local' and r['checks']['bank_rw']==1 and r['checks']['reuse_a']==0 and r['checks']['hold_cycles']==hold]
            for old,new in zip(base,candidate):
                if (old['reset_mode'],old['seed'])!=(new['reset_mode'],new['seed']):raise ValueError('comparison mixed random configuration')
                old_cycles=old['checks']['cycles'];new_cycles=new['checks']['cycles']
                local_comparisons.append(dict(hold_cycles=hold,reset_mode=old['reset_mode'],seed=old['seed'],
                    baseline_cycles=old_cycles,bank_rw_cycles=new_cycles,saved_cycles=old_cycles-new_cycles,speedup=old_cycles/new_cycles))
        report['local_comparisons']=local_comparisons
        report['runs']=runs;report['passed']=True
    except Exception as error:
        report['error']=type(error).__name__+': '+str(error);raise
    finally:
        report['output_sha256']={str(p.relative_to(a.out)):sha(p) for p in a.out.rglob('*') if p.is_file()
            and p.name!='result.json' and not any(x.startswith('obj-') for x in p.relative_to(a.out).parts) and p.suffix in ('.log','.json')}
        (a.out/'result.json').write_bytes((json.dumps(report,indent=2)+'\n').encode())
        print(json.dumps(dict(passed=report['passed'],result=str(a.out/'result.json'),error=report.get('error'))),flush=True)


if __name__=='__main__':main()
