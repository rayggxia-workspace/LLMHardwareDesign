"""Actual fusion traces, separately labelled finite-pipeline replay, native RTL."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys

from generate_fusion import generate, verify_sources, HERE

COMPARE=HERE.parent/'sram_port_compare'
sys.path.insert(0,str(COMPARE))
import compare_audit
import fusion_contract
import fusion_oracle
from fusion_audit import audit_case
from replay import replay_events

BASE=HERE.parent/'p_dma_study'
BEST='adaptive_prefix_pair_combine'
WORKLOADS=[('decode512','queued_pipe_w8',BEST),('decode512','queued_pipe_w16','adaptive'),
           ('decode2048','queued_pipe_w8',BEST),('prefill2','queued_pipe_w8',BEST)]


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def execute(command,log,cwd,env=None,expected=0):
    process=subprocess.run(list(map(str,command)),cwd=cwd,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    log.write_bytes(process.stdout)
    if process.returncode!=expected:
        raise RuntimeError(str(command)+' exit '+str(process.returncode)+' '+process.stdout.decode(errors='replace')[-3500:])
    return process.stdout.decode()


def prior_gate(args,lock):
    path=args.prior.resolve();manifest=path.with_name('run05-inputs.json')
    if path.name!='run05-result.json':raise ValueError('use frozen run05-result.json basename')
    for file in (path,manifest):
        if digest(file)!=lock['prerequisite_sha256'][file.name]:raise ValueError('run05 prerequisite SHA drift '+file.name)
    prior=json.loads(path.read_text(encoding='utf-8'));meta=json.loads(manifest.read_text(encoding='utf-8'))
    if prior.get('passed') is not True or not prior.get('default_phase_passed') or prior.get('default_full_result_replays')!=12:
        raise ValueError('run05 lacks accepted default full-regression receipt')
    if prior['source_commit']!=meta.get('source_commit'):raise ValueError('run05 source mismatch')
    return prior,dict(source_commit=prior['source_commit'],result_sha256=digest(path),inputs_sha256=digest(manifest))


def lookup(prior,workload,profile,variant,route,kib,ctx):
    rows=[c for c in prior['cases'] if (c['workload'],c['profile'],c['variant'],c['route'],c['P_KiB'],c['contexts'],c['P_port_quarters'],c['policy_KiB'])
          ==(workload,profile,variant,route,kib,ctx,4,16)]
    if len(rows)!=1:raise ValueError('missing/duplicate run05 reference '+str((workload,profile,route)))
    return rows[0]['result']


def plan(prior):
    configurations=[(w,p,v,r,k,c) for w,p,v in WORKLOADS for r,k,c in [('B16ctx8',16,8),('A64',64,1)]]
    configurations.append(('decode512','queued_pipe_w8',BEST,'A48',48,1))
    for cfg in configurations:lookup(prior,*cfg)
    jobs=[(*cfg,fusion,0) for fusion in (0,1) for cfg in configurations]
    for workload in ('decode512','prefill2'):
        for fee in (1,3):jobs.append((workload,'queued_pipe_w8',BEST,'B16ctx8',16,8,1,fee))
    return jobs


def analyse_case(row,old,trace,events,fusion,fee):
    checked=audit_case(row,old,trace,events,fusion,fee)
    replays=[replay_events(events,row,depth,trace=trace) for depth in (1,2,4,8)]
    mutations=[('hidden_M_work',lambda r:r.__setitem__('M_work_ticks',r['M_work_ticks']-1)),
        ('hidden_forward_bytes',lambda r:r['u_fusion_study'].__setitem__('forwarded_bytes',r['u_fusion_study']['forwarded_bytes']+4)),
        ('forward_overflow',lambda r:r['u_fusion_study'].__setitem__('forward_peak_bytes',257))]
    negatives=[]
    for label,mutate in mutations:
        bad=deepcopy(row);mutate(bad)
        try:audit_case(bad,old,trace,events,fusion,fee)
        except (AssertionError,ValueError):negatives.append(label)
        else:raise ValueError('fusion audit accepted '+label)
    return checked,replays,negatives


def small_traces(out):
    result=[]
    definitions=[('tail1',1,'chain'),('tail17',17,'chain'),('tail65',65,'chain'),
                 ('duplicate-input',65,'duplicate'),('multiple-users',65,'multiple'),
                 ('canonical-barrier',65,'canonical')]
    for name,n,kind in definitions:
        operators=[(3,'Product',[0,1])]
        if kind=='duplicate':operators.append((4,'Product',[3,3]))
        elif kind=='multiple':operators += [(4,'Product',[3,2]),(5,'Add',[3,0])]
        elif kind=='canonical':operators += [(4,'SiLU',[3]),(5,'Product',[4,2])]
        else:operators.append((4,'Product',[3,2]))
        nt=operators[-1][0]+1
        text=f'{nt} {len(operators)} 1\n'
        text+=''.join(f'{i} {n} 32 {int(i<3)}\n' for i in range(nt))
        text+=''.join(f'{i} {op} {n} 1 1 1 1 0 1 {len(inputs)} '+ ' '.join(map(str,inputs))+'\n'
                      for i,op,inputs in operators)
        path=out/('small-'+name+'.trace');path.write_bytes(text.encode())
        result.append((name,path,1 if kind=='chain' else 0))
    return result


def main():
    parser=argparse.ArgumentParser()
    for name in ('inputs','out','prior'):parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();inputs=args.inputs.resolve();out=args.out.resolve()
    lock=verify_sources();prior,prior_index=prior_gate(args,lock);jobs=plan(prior)
    for name,value in lock['input_sha256'].items():
        if digest(inputs/name)!=value:raise ValueError('fusion input SHA drift '+name)
    workers=min(4,int(os.environ.get('SLURM_CPUS_PER_TASK','0')))
    if workers<1:raise ValueError('requires allocated Slurm CPUs')
    out.mkdir(parents=True,exist_ok=False)
    (out/'generated').mkdir()
    (out/'m-profile.log').write_bytes((inputs/'m-profile.log').read_bytes())
    generate(out)
    for name in ('matrix.inc','context_worker.inc','context_detail.hpp','detail.hpp'):
        if digest(out/name)!=prior['generated_sha256'][name]:raise ValueError('changed frozen P source '+name)
    manifest=out.parent/'inputs.json'
    source_commit=json.loads(manifest.read_text(encoding='utf-8'))['source_commit']
    execute([sys.executable,'-B',HERE/'parser_selftest.py'],out/'native-parser-selftest.log',out)
    execute([sys.executable,'-B',HERE/'run_native.py','--repo',HERE.parents[2],'--out',out/'native',
             '--workers',workers,'--manifest',manifest],out/'native-run.log',out)
    native=json.loads((out/'native/result.json').read_text())
    if not native['passed'] or native['source_commit']!=source_commit:raise ValueError('native receipt source mismatch')
    flags=['-std=c++17','-O2','-Wall','-Wextra','-Werror'];prefix=Path('/public/home/yuzelu/opt/systemc-3.0.2-issue219')
    execute(['g++',*flags,out/'model.cpp','-I'+str(out),'-I'+str(prefix/'include'),'-L'+str(prefix/'lib'),
             '-Wl,-rpath,'+str(prefix/'lib'),'-lsystemc','-o',out/'model'],out/'build.log',out)
    execute(['g++',*flags,BASE/'upstream/kernel_probe.cpp','-o',out/'kernel_probe'],out/'kernel-build.log',out)
    env=dict(os.environ,BLOCK_STUDY_MODEL=str(out/'model'))
    # Legacy helpers generate their own traces. They must not inherit a
    # full-case event filename or its trace identity from the caller.
    env.pop('U_FUSION_EVENTS',None)
    env.pop('U_FUSION_TRACE_SHA256',None)
    for script in ('check_kernels.py','validate.py','smoke.py'):
        execute([sys.executable,'-B',BASE/'upstream'/script],out/(script+'.log'),out,env)
    oracle=fusion_oracle.run();(out/'oracle.json').write_bytes((json.dumps(oracle,indent=2)+'\n').encode())
    replay_selftest=json.loads(execute([sys.executable,'-B',HERE/'replay_selftest.py'],out/'replay-selftest.log',out))
    if replay_selftest.get('passed') is not True:raise ValueError('replay selftest failed')
    inventories={w:fusion_contract.analyse(inputs/(w+'.trace')) for w in sorted({j[0] for j in jobs})}
    (out/'trace-inventory.json').write_bytes((json.dumps(inventories,indent=2)+'\n').encode())
    def case(item):
        workload,profile,variant,route,kib,ctx,fusion,fee=item
        name=f'{workload}-{profile}-{route}-f{fusion}-c{fee}'
        trace=inputs/(workload+'.trace');events=out/(name+'.jsonl')
        command=[out/'model',trace,profile,variant,ctx,1,1,kib,1,4,16,fusion,fee]
        text=execute(command,out/(name+'.log'),out,dict(env,U_FUSION_EVENTS=str(events),U_FUSION_TRACE_SHA256=digest(trace)))
        if 'MODEL_FAILURE' in text or 'SystemC 3.0.2' not in text:raise ValueError('model failed '+name)
        rows=[json.loads(line[7:]) for line in text.splitlines() if line.startswith('RESULT ')];assert len(rows)==1
        row=rows[0];old=lookup(prior,workload,profile,variant,route,kib,ctx)
        audit=compare_audit.check(row,trace,kib*1024,True,4,ctx,1,True)
        regression=None
        if not fusion:
            clean=deepcopy(row);clean.pop('u_fusion_study')
            if clean!=old:raise ValueError('complete run05 regression failed '+name)
            regression=dict(passed=True,complete_fields_equal=True)
        # Independent event/cache audit and constrained replay are integrated below.
        checked,replays,negatives=analyse_case(row,old,trace,events,fusion,fee)
        record=dict(workload=workload,profile=profile,variant=variant,route=route,P_KiB=kib,contexts=ctx,
            fusion=fusion,forward_control_cycles=fee,result=row,audit=audit,fusion_audit=checked,
            default_regression=regression,negative_checks=negatives,pipeline_counterfactual=replays,
            speedup_vs_actual_run05=old['seconds']/row['seconds'],log_sha256=digest(out/(name+'.log')),
            events_sha256=digest(events),events_file=events.name)
        (out/(name+'.json')).write_bytes((json.dumps(record,indent=2)+'\n').encode())
        print(json.dumps(dict(case=name,tokens_s=row['tokens_per_second'],fusion=fusion,fee=fee)),flush=True)
        return record
    records=[]
    for defaults in (True,False):
        batch=[item for item in jobs if (item[-2]==0)==defaults]
        with ThreadPoolExecutor(max_workers=workers) as pool:records+=list(pool.map(case,batch))
    small=[]
    for label,trace,edges in small_traces(out):
        previous=None
        for fusion in (0,1):
            name=f'small-{label}-f{fusion}';events=out/(name+'.jsonl')
            text=execute([out/'model',trace,'queued_pipe_w8',BEST,8,1,1,16,1,4,16,fusion,0],
                         out/(name+'.log'),out,dict(env,U_FUSION_EVENTS=str(events),U_FUSION_TRACE_SHA256=digest(trace)))
            lines=[json.loads(line[7:]) for line in text.splitlines() if line.startswith('RESULT ')];assert len(lines)==1
            row=lines[0]
            if not fusion:
                previous=deepcopy(row);previous.pop('u_fusion_study')
            checked,replays,negatives=analyse_case(row,previous,trace,events,fusion,0)
            if row['u_fusion_study']['eligible_graph_edges']!=edges:raise ValueError('small edge coverage '+label)
            record=dict(name=label,fusion=fusion,result=row,audit=checked,pipeline_counterfactual=replays,
                        negative_checks=negatives,trace_sha256=digest(trace),events_sha256=digest(events),log_sha256=digest(out/(name+'.log')))
            (out/(name+'.json')).write_bytes((json.dumps(record,indent=2)+'\n').encode());small.append(record)
    invalid=[]
    for label,fusion,fee in [('unsupported-fusion','2','0'),('unsupported-fee','1','2'),('numeric-tail','1','1junk')]:
        text=execute([out/'model',inputs/'decode512.trace','queued_pipe_w8',BEST,8,1,1,16,1,4,16,fusion,fee],
                     out/('reject-'+label+'.log'),out,expected=2)
        if 'RESULT ' in text:raise ValueError('invalid CLI executed model')
        invalid.append(label)
    for kind in ('source_sha256','prerequisite_sha256'):
        bad=deepcopy(lock);name=next(iter(bad[kind]));value=bad[kind][name]
        bad[kind][name]=('0' if value[0]!='0' else '1')+value[1:]
        try:
            if kind=='source_sha256':verify_sources(bad)
            else:prior_gate(args,bad)
        except ValueError:pass
        else:raise ValueError('source/prior verifier accepted drift '+kind)
    report=dict(passed=True,issue=247,source_commit=source_commit,prior_run05=prior_index,
        scope='actual single-E adjacent fusion SystemC; separately labelled finite-stage pipeline counterfactual; production-S16 pair RTL measured separately',
        default_phase_passed=True,default_full_result_replays=9,cases=records,small_cases=small,
        native_result_sha256=digest(out/'native/result.json'),native_summary=native,
        oracle=oracle,replay_selftest=replay_selftest,trace_inventories=inventories,invalid_CLI_rejected=invalid,source_and_prior_SHA_negative=True,
        versions=dict(python=platform.python_version(),SystemC='3.0.2',gcc=subprocess.check_output(['g++','--version'],text=True).splitlines()[0]),
        input_sha256=lock['input_sha256'],source_lock=lock,
        generated_sha256={p.name:digest(p) for p in out.iterdir() if p.suffix in ('.cpp','.hpp','.inc')})
    (out/'result.json').write_bytes((json.dumps(report,indent=2)+'\n').encode())
    print('U_FUSION_STUDY_PASS '+str(len(records)),flush=True)


if __name__=='__main__':main()
