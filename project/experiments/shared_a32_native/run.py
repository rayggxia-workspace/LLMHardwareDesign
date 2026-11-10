"""Slurm-only native 16/32 B-per-P RTL tests and equal-work microbenchmarks."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import platform
import re
import signal
import subprocess
import time
import traceback

HERE = Path(__file__).resolve().parent
SEEDS = ((1, 247), (2, 247), (2, 248))
BASELINE = 'project/experiments/shared_a32_baseline'
M_SOURCES = ['project/rtl/block_v2/block_v2_m.sv', 'project/rtl/block_v2/block_v2_m_context.sv']


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def require(ok, message):
    if not ok:
        raise ValueError(message)


def main():
    p = argparse.ArgumentParser()
    for name in ('repo', 'out', 'manifest'):
        p.add_argument('--'+name, type=Path, required=True)
    p.add_argument('--workers', type=int, default=4)
    p.add_argument('--components', choices=('units', 'pair', 'compat', 'all'), default='all')
    p.add_argument('--area', action='store_true')
    p.add_argument('--build-timeout', type=int, default=1800)
    p.add_argument('--run-timeout', type=int, default=300)
    a = p.parse_args()
    require(1 <= a.build_timeout <= 1800 and 1 <= a.run_timeout <= 600, 'timeouts must be positive and bounded')
    require(not a.area or a.components in ('units','all'), 'area requires the complete unit functional gate')
    require(re.fullmatch(r'\d+', os.environ.get('SLURM_JOB_ID', '')) is not None and
            1 <= a.workers <= min(4, int(os.environ.get('SLURM_CPUS_PER_TASK', '0'))), 'actual Slurm 1..4 CPU allocation required')
    a.repo, a.out = a.repo.resolve(), a.out.resolve()
    a.out.mkdir(parents=True, exist_ok=False)
    old = load(a.repo/'project/experiments/shared32_native/run.py', 'frozen_native_helpers')
    sha = old.sha
    r = dict(passed=False, functional_passed=False, scope='Actual native RTL microbenchmarks; no full-model token/s or physical frequency qualification',
             job=os.environ['SLURM_JOB_ID'], workers=a.workers, node=platform.node(), components=a.components,
             source_commit=None, versions=dict(python=platform.python_version()), commands=[], tests={}, errors=[],
             exact_16B_compatibility_pairs=0, equal_work_comparisons=[], mapped_area=None,
             native_full_model_tokens_per_second=None, physical_clock_qualified=False)

    def save():
        old.dump(a.out/'result.json', r)

    def execute(cmd, log, timeout=None):
        cmd=list(map(str,cmd)); target=a.out/log;target.parent.mkdir(parents=True, exist_ok=True)
        start=time.monotonic(); timed_out=False
        with target.open('wb') as stream:
            proc=subprocess.Popen(cmd,cwd=a.repo,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True)
            try: code=proc.wait(timeout=timeout or a.build_timeout)
            except subprocess.TimeoutExpired:
                timed_out=True;os.killpg(proc.pid,signal.SIGKILL);proc.wait();code=proc.returncode
        r['commands'].append(dict(command=cmd,log=log,exit_code=code,timed_out=timed_out,seconds=time.monotonic()-start,sha256=sha(target)));save()
        text=target.read_text(encoding='utf8',errors='replace')
        require(code==0 and not timed_out, log+' failed: '+text[-2500:])
        require(re.search(r'%Warning-(?:PINMISSING|PINNOTFOUND)',text) is None, log+' has unconnected production ports')
        require(re.search(r'%Warning-[^:]+: [^\n]*tb_a32_',text) is None, log+' has a warning in the new testbench')
        return text

    def parse(text, kind):
        if kind in ('pool','legacy'):
            return old.parse_receipts(text,'pool' if kind=='pool' else 'pair')
        prefix={'m':'A32_M','pair':'A32_PAIR','control':'A32_CONTROL'}[kind]
        passed=re.findall(r'^'+prefix+r'_PASS(?: .*)?$',text,re.M)
        measures=re.findall(r'^'+prefix+r'_MEASURE .+$',text,re.M)
        require(len(passed)==1 and bool(measures),kind+' pass/measurement absent or duplicated')
        receipt=dict(checks=old.fields(passed[0]),measurements=[old.fields(x) for x in measures])
        require(all(type(m.get('cycles')) is int and m['cycles']>0 for m in receipt['measurements']), 'invalid measured cycles')
        if kind=='m':require(receipt['checks']['numeric']==2432 and receipt['checks']['shapes']==64,'M numerical coverage missing')
        if kind=='pair':require(receipt['checks']['numeric']==4864 and receipt['checks']['scenarios']==len(measures)==64,'pair numerical coverage missing')
        if kind=='pair':require({m['scenario'] for m in receipt['measurements']}==set(range(64)),'pair shape identity missing/duplicated')
        if kind=='control':
            require(len(receipt['measurements'])==1,'control measurement count changed')
            for key in ('clear_all','clear_same','clear_other','start_same','busy_other','tail_garbage','reset_clear'):
                require(receipt['measurements'][0].get(key)==1,'control coverage missing: '+key)
            require(receipt['measurements'][0].get('legal_pairs')==5,'legal pair coverage missing')
        return receipt

    def test(label, top, bench, sources, parameters, kind, legacy_warnings=False):
        obj=a.out/('obj-'+label)
        execute([old.VERILATOR,'--binary','--timing','--assert','--timescale','1ns/1ps',
                 *(['-Wno-fatal'] if legacy_warnings else []),'--x-initial','unique','--x-assign','unique',
                 '-j',a.workers,'--top-module',top,'--Mdir',obj,*parameters,
                 '-I'+str(a.repo/'project/rtl/block_v2'),bench,*sources,*([old.BANK] if kind in ('pool','pair','legacy') else [])],label+'-build.log')
        records=[];r['tests'][label]=dict(passed=False,parameters=parameters,runs=records)
        for mode,seed in SEEDS:
            log=label+'-run-'+str(mode)+'-'+str(seed)+'.log'
            output=execute([obj/('V'+top),'+verilator+rand+reset+'+str(mode),'+verilator+seed+'+str(seed),'+SEED='+str(seed)],log,a.run_timeout)
            record=dict(reset_mode=mode,seed=seed,log=log,log_sha256=sha(a.out/log),**parse(output,kind))
            if label.startswith(('baseline-','candidate16-')):
                events=[line for line in output.splitlines() if line.startswith('COMPAT_EVENT ')]
                require(bool(events),'default compatibility events missing')
                events.sort(key=lambda line:(int(re.search(r'cycle=(\d+)',line).group(1)),line))
                event_file=a.out/(label+'-events-'+str(mode)+'-'+str(seed)+'.log')
                event_file.write_text('\n'.join(events)+'\n',encoding='utf8')
                record.update(event_count=len(events),event_sha256=sha(event_file),event_log=event_file.name,
                              event_order='cycle then observer kind/client; no timing or payload fields removed')
            records.append(record);save()
        r['tests'][label]['passed']=True;save()

    try:
        manifest=json.loads(a.manifest.read_bytes())
        required={p.relative_to(a.repo).as_posix() for p in HERE.iterdir() if p.is_file()}
        required.update(['project/experiments/shared32_native/'+n for n in ('run.py','tb_shared_pool.sv','tb_shared_pair.sv')])
        pair_names=[old.PAIR,old.POOL,*old.GROUP_SOURCES]
        required.update(pair_names);required.update(M_SOURCES)
        required.add('project/rtl/block_v2/block_v2_g_tables.svh')
        required.update(p.relative_to(a.repo).as_posix() for p in (a.repo/BASELINE).iterdir() if p.is_file())
        r['source_commit']=old.validate_manifest(a.repo,manifest,required)
        r['manifest_sha256']=sha(a.manifest);r['source_sha256']={n:sha(a.repo/n) for n in sorted(required)}
        require(sha(old.BANK)==old.BANK_SHA,'actual SRAM model identity changed')
        r['bank']=dict(path=str(old.BANK),sha256=old.BANK_SHA)
        r['versions']['verilator']=execute([old.VERILATOR,'--version'],'verilator-version.log',30).strip()
        r['versions']['gcc']=execute(['g++','--version'],'gcc-version.log',30).splitlines()[0]
        r['verilator_binary_sha256']=sha(old.VERILATOR)
        gen=load(HERE/'generate.py','a32_generator');generated=a.out/'generated'
        r['bench_generation']=gen.generate(a.repo,generated);save()
        pair_sources=[a.repo/n for n in pair_names];m_sources=[a.repo/n for n in M_SOURCES]
        if a.components in ('units','all'):
            for words in (1,2):
                execute([old.VERILATOR,'--lint-only','--timing','--timescale','1ns/1ps','--top-module','shared_a_pool32',
                         '-GA_WORDS_PER_BEAT='+str(words),a.repo/old.POOL,old.BANK],'pool-w'+str(words)+'-strict-lint.log')
                test('pool-w'+str(words),'tb_a32_pool',generated/'tb_a32_pool.sv',[a.repo/old.POOL],['-GWORDS='+str(words)],'pool')
                for contexts in (0,8):
                    test('m-w'+str(words)+'-c'+str(contexts),'tb_a32_m',HERE/'tb_a32_m.sv',m_sources,
                         ['-GWORDS='+str(words),'-GCONTEXTS='+str(contexts)],'m')
            for contexts in (0,8):
                test('control-c'+str(contexts),'tb_a32_control',HERE/'tb_a32_control.sv',m_sources,['-GCONTEXTS='+str(contexts)],'control')
        if a.components in ('compat','all'):
            lock=json.loads((a.repo/BASELINE/'source.json').read_bytes())
            require(lock['source_commit']=='2fc03de589e65f28d362128f9d988034429fd50c' and len(lock['files'])==5,'baseline source lock changed')
            substitutions={}
            for original,entry in lock['files'].items():
                frozen=a.repo/BASELINE/entry['snapshot'];require(sha(frozen)==entry['sha256'],'frozen 16B RTL changed');substitutions[original]=frozen
            baseline_sources=[substitutions.get(n,a.repo/n) for n in pair_names]
            r['compatibility_baseline']=lock
            for share,rw in ((0,0),(1,0),(0,1),(1,1)):
                suffix='s'+str(share)+'-rw'+str(rw);params=['-GSHARED='+str(share),'-GTRUE_RW='+str(rw)]
                for variant,bench,sources in [('baseline','tb_compat_baseline.sv',baseline_sources),('candidate16','tb_compat_candidate.sv',pair_sources),('candidate32','tb_lifecycle32.sv',pair_sources)]:
                    test(variant+'-'+suffix,'tb_shared_pair',generated/bench,sources,params,'legacy',True)
                for oldrun,newrun in zip(r['tests']['baseline-'+suffix]['runs'],r['tests']['candidate16-'+suffix]['runs']):
                    require(all(oldrun[k]==newrun[k] for k in ('seed','reset_mode','checks','measurements')),'default16 compatibility differs: '+suffix)
                    require(oldrun['event_count']==newrun['event_count'] and
                            (a.out/oldrun['event_log']).read_bytes()==(a.out/newrun['event_log']).read_bytes(),
                            'default16 cycle/handshake/payload event mismatch: '+suffix)
                    r['exact_16B_compatibility_pairs']+=1
                save()
        if a.components in ('pair','all'):
            for contexts in (0,8):
                for words in (1,2):
                    test('pair-w'+str(words)+'-c'+str(contexts),'tb_a32_pair',generated/'tb_a32_pair.sv',pair_sources,
                         ['-GWORDS='+str(words),'-GCONTEXTS='+str(contexts)],'pair',True)
                for one,two in zip(r['tests']['pair-w1-c'+str(contexts)]['runs'],r['tests']['pair-w2-c'+str(contexts)]['runs']):
                    for oldrow,newrow in zip(one['measurements'],two['measurements']):
                        timing={'words','cycles','initialization_cycles','processing_cycles','load_cycles','compute_cycles','feed_span_cycles','a_beats'}
                        require({k:v for k,v in oldrow.items() if k not in timing}=={k:v for k,v in newrow.items() if k not in timing},'unequal payload/commands/numerical work')
                        require(oldrow['initialization_cycles']==newrow['initialization_cycles'] and oldrow['compute_cycles']==newrow['compute_cycles'],'unrelated setup or M arithmetic timing changed')
                    oldtime=sum(m['processing_cycles'] for m in one['measurements']);newtime=sum(m['processing_cycles'] for m in two['measurements'])
                    r['equal_work_comparisons'].append(dict(contexts=contexts,seed=one['seed'],reset_mode=one['reset_mode'],scenarios=64,
                        measured_processing_cycles_16=oldtime,measured_processing_cycles_32=newtime,speed_ratio=oldtime/newtime,
                        no_token_s_projection=True))
                save()
        r['functional_passed']=all(t['passed'] for t in r['tests'].values()) and bool(r['tests'])
        if a.area:
            require(r['functional_passed'],'area functional gate failed')
            r['mapped_area']=load(HERE/'area.py','a32_area').run_area(a.repo,a.out/'area');save()
        r['passed']=r['functional_passed'] and (not a.area or r['mapped_area']['status']=='passed')
    except Exception as e:
        r['errors'].append(dict(error=str(e),traceback=traceback.format_exc()))
    finally:
        r['output_files_sha256']={p.relative_to(a.out).as_posix():sha(p) for p in a.out.rglob('*') if p.is_file() and p!=a.out/'result.json' and not any(v.startswith('obj-') for v in p.relative_to(a.out).parts)}
        save();print(json.dumps(dict(passed=r['passed'],functional_passed=r['functional_passed'],tests=len(r['tests']),errors=r['errors'],result=str(a.out/'result.json'))),flush=True)
    return 0 if r['passed'] else 1


if __name__=='__main__':
    raise SystemExit(main())
