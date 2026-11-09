"""Frozen regression, capacity/port factors, route comparison and cost grid."""
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

from generate_compare import generate,verify_sources,HERE,BASE
import compare_audit

BEST='adaptive_prefix_pair_combine'


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def execute(command,log,cwd,env=None,expected=0):
    process=subprocess.run(list(map(str,command)),cwd=cwd,env=env,
                           stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    log.write_bytes(process.stdout)
    if process.returncode!=expected:
        raise RuntimeError(str(command)+' exit '+str(process.returncode)+' '+process.stdout.decode(errors='replace')[-3000:])
    return process.stdout.decode()


def old_capacity_key(record):
    cycles=record['P_service_cycles']
    return (record['workload'],record['profile'],record['variant'],1,1,1,
            record['P_KiB'],0,int(cycles*4))


def old_hardware_key(record):
    c=record['contract']
    return (record['workload'],record['profile'],record['variant'],record['contexts'],
            record['switch_cycles'],int(record['reuse_A']),16,int(c['split_P_read_write_ports']),4)


def plan(capacity,stage3):
    """Ordered unique cases; first group must pass old whole-result regressions."""
    items={}
    def add(key,role):
        if key not in items:items[key]=[]
        if role not in items[key]:items[key].append(role)
    def key(workload,profile,variant,ctx,kib,dual,q=4,switch=1,reuse=1):
        return (workload,profile,variant,ctx,switch,reuse,kib,int(dual),q)
    for record in capacity['cases']:
        if record['workload']=='decode512' and record['P_KiB'] in (16,48,64):
            add(old_capacity_key(record),'regression-246')
    for record in stage3['cases']:
        c=record['contract']
        if record['workload']=='decode512' and c['P_count']==2 and c['vector_lanes']==4:
            add(old_hardware_key(record),'regression-247')
    for kib in (16,48,64):
        for dual in (0,1):add(key('decode512','queued_pipe_w8',BEST,1,kib,dual),'factorial-W8')
    for kib in (16,48,64):add(key('decode512','queued_pipe_w8',BEST,8,kib,1),'overlap-W8')
    for switch in (3,8):add(key('decode512','queued_pipe_w8',BEST,8,16,1,switch=switch),'switch-cost')
    for kib,ctx in ((48,1),(64,1),(16,8)):
        for q in (4,5,6,8):add(key('decode512','queued_pipe_w8',BEST,ctx,kib,1,q),'port-cost-grid')
    for kib in (16,48,64):
        for ctx in (1,8):add(key('decode512','queued_pipe_w16','adaptive',ctx,kib,1),'W16-routes')
    for workload in ('decode2048','prefill2'):
        for kib in (16,48,64):
            for dual in (0,1):add(key(workload,'queued_pipe_w8',BEST,1,kib,dual),'workload-factorial')
            add(key(workload,'queued_pipe_w8',BEST,8,kib,1),'workload-overlap')
    for workload,kib in (('tail-n1-k11009',48),('tail-n17-k11009',48),('tail-n129-k16385',64)):
        for ctx in (1,8):add(key(workload,'queued_pipe_w8','observe',ctx,kib,1),'tail-contract')
    return items


def prerequisites(args,lock):
    receipts={};locations={}
    for name in ('capacity','stage1','stage2','stage3'):
        path=getattr(args,name).resolve();manifest=path.with_name(name+'-inputs.json')
        if path.name!=name+'-result.json':raise ValueError('use frozen prerequisite basename '+name+'-result.json')
        for file in (path,manifest):
            if digest(file)!=lock['prerequisite_sha256'][file.name]:raise ValueError('prerequisite SHA drift '+file.name)
        report=json.loads(path.read_text(encoding='utf-8'));meta=json.loads(manifest.read_text(encoding='utf-8'))
        if report.get('passed') is not True or not report.get('source_commit'):
            raise ValueError('missing actual passed/source_commit '+name)
        if meta.get('source_commit')!=report['source_commit']:raise ValueError('prerequisite source mismatch '+name)
        receipts[name]=report
        locations[name]=dict(source_commit=report['source_commit'],result_sha256=digest(path),inputs_sha256=digest(manifest))
    if not receipts['stage1'].get('complete_legacy_baseline_exact'):raise ValueError('stage1 whole-result gate missing')
    if not receipts['stage2'].get('stage1_generated_sources_exact'):raise ValueError('elastic gate source proof missing')
    if receipts['stage2'].get('stage1_sha256')!=locations['stage1']['result_sha256']:
        raise ValueError('elastic gate does not bind given stage1 receipt')
    if not receipts['stage3'].get('baseline_complete_stage1_exact'):raise ValueError('hardware baseline gate missing')
    for name in ('stage1','stage2'):
        old=receipts['stage3']['prerequisite_receipts'][name]
        if old['sha256']!=locations[name]['result_sha256'] or old['source_commit']!=receipts[name]['source_commit']:
            raise ValueError('hardware gate prerequisite mismatch '+name)
    return receipts,locations


def write_tail_traces(folder):
    hashes={}
    for n,k in ((1,11009),(17,11009),(129,16385)):
        name=f'tail-n{n}-k{k}'
        text=f'3 1 1\n0 {k} 32 1\n1 {n*k} 16 1\n2 {n} 32 0\n2 Dot {n} 1 {n} {k} 1 0 0 2 0 1\n'
        path=folder/(name+'.trace');path.write_bytes(text.encode());hashes[path.name]=digest(path)
    return hashes


def main():
    parser=argparse.ArgumentParser()
    for name in ('inputs','out','capacity','stage1','stage2','stage3'):
        parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();out=args.out.resolve();inputs=args.inputs.resolve()
    lock=verify_sources();prior,prior_index=prerequisites(args,lock)
    for name,value in lock['input_sha256'].items():
        if digest(inputs/name)!=value:raise ValueError('input SHA drift '+name)
    if int(os.environ.get('SLURM_CPUS_PER_TASK','0'))<1:raise ValueError('requires allocated Slurm CPUs')
    workers=min(4,int(os.environ['SLURM_CPUS_PER_TASK']))
    out.mkdir(parents=True,exist_ok=False);generated=out/'generated';generated.mkdir()
    (out/'m-profile.log').write_bytes((inputs/'m-profile.log').read_bytes())
    tail_sha=write_tail_traces(generated);generate(out)
    prefix=Path('/public/home/yuzelu/opt/systemc-3.0.2-issue219')
    flags=['-std=c++17','-O2','-Wall','-Wextra','-Werror']
    execute(['g++',*flags,out/'model.cpp','-I'+str(out),'-I'+str(prefix/'include'),'-L'+str(prefix/'lib'),
             '-Wl,-rpath,'+str(prefix/'lib'),'-lsystemc','-o',out/'model'],out/'build.log',out)
    execute(['g++',*flags,BASE/'upstream/kernel_probe.cpp','-o',out/'kernel_probe'],out/'kernel-build.log',out)
    env=dict(os.environ,BLOCK_STUDY_MODEL=str(out/'model'))
    for script in ('check_kernels.py','validate.py','smoke.py'):
        execute([sys.executable,'-B',BASE/'upstream'/script],out/(script+'.log'),out,env)
    cap_index={old_capacity_key(record):record['result'] for record in prior['capacity']['cases']
               if record['P_KiB'] in (16,48,64)}
    hw_index={old_hardware_key(record):record['result'] for record in prior['stage3']['cases']
              if record['contract']['P_count']==2 and record['contract']['vector_lanes']==4}
    U_references={(record['workload'],record['profile'],record['variant']):record['result']
                  for record in prior['stage1']['cases'] if record['contexts']==1 and record['switch_cycles']==1}
    jobs=plan(prior['capacity'],prior['stage3']);record_index={};records=[]
    def case(key):
        workload,profile,variant,ctx,switch,reuse,kib,dual,q=key
        trace=(generated if workload.startswith('tail-') else inputs)/(workload+'.trace')
        name=f'{workload}-{profile}-{variant}-c{ctx}-s{switch}-a{reuse}-k{kib}-d{dual}-q{q}'
        text=execute([out/'model',trace,profile,variant,ctx,switch,reuse,kib,dual,q],out/(name+'.log'),out)
        if 'MODEL_FAILURE' in text or 'SystemC 3.0.2' not in text:raise ValueError('missing model success/version '+name)
        rows=[json.loads(line[7:]) for line in text.splitlines() if line.startswith('RESULT ')];assert len(rows)==1
        row=rows[0]
        checked=compare_audit.check(row,trace,kib*1024,bool(dual),q,ctx,switch,bool(reuse))
        if not workload.startswith('tail-'):
            U_check=compare_audit.check_U_reference(row,U_references[(workload,profile,variant)])
        else:
            assert row['vector_work_ticks']==0 and row['U_cache_peak_bytes']==0 and row['KV_state_write_bytes']==0
            assert row['detail']['S_calendars'][3]['service_subcycles']==0
            assert all(channel['flows'][flow][key]==0 for channel in row['detail']['channels']
                       for flow in ('U_read','U_write','KV_write')
                       for key in ('logical_read','logical_write','bus_read','bus_write','descriptors'))
            U_check=dict(passed=True,scope='generated pure-Dot edge has no U operations; no historical edge reference')
        regressions=[]
        if key in cap_index:
            compare_audit.assert_regression(row,cap_index[key],kind='246');regressions.append('246-full-result')
        if key in hw_index:
            compare_audit.assert_regression(row,hw_index[key],kind='247');regressions.append('247-full-result')
        negatives=compare_audit.reject_checks(row,trace,kib*1024,bool(dual),q,ctx,switch,bool(reuse))
        record=dict(workload=workload,profile=profile,variant=variant,contexts=ctx,switch_cycles=switch,
            reuse_A=bool(reuse),P_KiB=kib,dual_ports=bool(dual),P_port_quarters=q,
            roles=jobs[key],result=row,audit=checked,U_reference=U_check,regressions=regressions,negative_checks=negatives,
            log_sha256=digest(out/(name+'.log')))
        (out/(name+'.json')).write_bytes((json.dumps(record,indent=2)+'\n').encode())
        print(json.dumps(dict(case=name,tokens_s=row['tokens_per_second'],regressions=regressions,
                             bus_bytes=row['read_bus_bytes']+row['write_bus_bytes'])),flush=True)
        return key,record
    # No new optimization result can be accepted until all relevant historical
    # baselines have actually been rerun through this same binary.
    for regression in (True,False):
        batch=[key for key,roles in jobs.items() if any(role.startswith('regression-') for role in roles)==regression]
        with ThreadPoolExecutor(max_workers=workers) as pool:
            for key,record in pool.map(case,batch):records.append(record);record_index[key]=record
    def get(workload,profile,variant,ctx,kib,dual,q=4,switch=1):
        return record_index[(workload,profile,variant,ctx,switch,1,kib,int(dual),q)]
    factors=[]
    for kib in (48,64):
        b=get('decode512','queued_pipe_w8',BEST,1,16,0)['result']['seconds']
        s=get('decode512','queued_pipe_w8',BEST,1,kib,0)['result']['seconds']
        p=get('decode512','queued_pipe_w8',BEST,1,16,1)['result']['seconds']
        both=get('decode512','queued_pipe_w8',BEST,1,kib,1)['result']['seconds']
        factors.append(dict(P_KiB=kib,capacity_speedup=b/s,port_speedup=b/p,combined_speedup=b/both,
                            port_speedup_at_larger_capacity=s/both,seconds_interaction=(both-s)-(p-b)))
    overlaps=[]
    for workload,profile,variant in [('decode512','queued_pipe_w8',BEST),('decode512','queued_pipe_w16','adaptive'),
                                     ('decode2048','queued_pipe_w8',BEST),('prefill2','queued_pipe_w8',BEST)]:
        for kib in (48,64):
            one=get(workload,profile,variant,1,kib,1)['result'];eight=get(workload,profile,variant,8,kib,1)['result']
            assert all(p['enabled_calls']==0 for p in eight['context_study']['P'])
            a=deepcopy(one);b=deepcopy(eight);del a['context_study'];del b['context_study']
            assert a==b,'resident capacity/context overlap changed real work or timing'
            overlaps.append(dict(workload=workload,profile=profile,P_KiB=kib,all_real_metrics_exact=True))
    reference=get('decode512','queued_pipe_w8',BEST,8,16,1)['result']['seconds'];grid=[]
    for kib,ctx in ((48,1),(64,1),(16,8)):
        for q in (4,5,6,8):
            r=get('decode512','queued_pipe_w8',BEST,ctx,kib,1,q)['result']
            fair=get('decode512','queued_pipe_w8',BEST,8,16,1,q)['result']['seconds']
            grid.append(dict(P_KiB=kib,contexts=ctx,P_cycles_per_64B=q/4,seconds=r['seconds'],
                tokens_s=r['tokens_per_second'],speedup_vs_16ctx8_q4=reference/r['seconds'],
                speedup_vs_16ctx8_same_cost=fair/r['seconds']))
    # Invalid user-facing arguments must be rejected before graph execution.
    invalid=[]
    for label,tail in [('capacity',['32','1','4']),('cost',['64','1','7']),('numeric-tail',['64junk','1','4'])]:
        text=execute([out/'model',inputs/'decode512.trace','queued_pipe_w8',BEST,1,1,1,*tail],
                     out/('reject-cli-'+label+'.log'),out,expected=2)
        assert 'RESULT ' not in text;invalid.append(label)
    text=execute([out/'model',inputs/'decode512.trace','packed_k32','observe',1,1,1,16,1,4],
                 out/'reject-cli-profile.log',out,expected=2)
    assert 'RESULT ' not in text;invalid.append('non-comparison-profile')
    source_negative=compare_audit.source_lock_negative(HERE,lock['source_sha256'])
    bad_lock=deepcopy(lock);name=next(iter(bad_lock['source_sha256']))
    value=bad_lock['source_sha256'][name];bad_lock['source_sha256'][name]=('0' if value[0]!='0' else '1')+value[1:]
    try:verify_sources(bad_lock)
    except ValueError:generator_lock_negative=True
    else:raise ValueError('actual generator source verifier accepted drift')
    bad_prerequisite=deepcopy(lock);name=next(iter(bad_prerequisite['prerequisite_sha256']))
    value=bad_prerequisite['prerequisite_sha256'][name]
    bad_prerequisite['prerequisite_sha256'][name]=('0' if value[0]!='0' else '1')+value[1:]
    try:prerequisites(args,bad_prerequisite)
    except ValueError:prerequisite_lock_negative=True
    else:raise ValueError('actual prerequisite verifier accepted SHA drift')
    report=dict(passed=True,issue=247,source_commit=json.loads((out.parent/'inputs.json').read_text(encoding='utf-8'))['source_commit'],
        scope='same binary capacity/port/context conditional architecture comparison; no production RTL/physical/frequency/energy qualification',
        prerequisite_receipts=prior_index,regression_phase_passed=True,cases=records,factorial_W8=factors,
        resident_context_overlap=overlaps,port_cost_grid=grid,
        port_grid_scope='measured discrete occupancy samples; no linear interpolation or physical-clock equivalence',
        invalid_CLI_rejected=invalid,source_lock_negative=source_negative,generator_lock_negative=generator_lock_negative,
        prerequisite_lock_negative=prerequisite_lock_negative,
        fixed_P_count=2,fixed_U_bytes=16384,fixed_vector_lanes=4,fixed_bandwidth_B_s=17100000000,
        versions=dict(python=platform.python_version(),SystemC='3.0.2',gcc=subprocess.check_output(['g++','--version'],text=True).splitlines()[0]),
        input_sha256=lock['input_sha256'],generated_trace_sha256=tail_sha,
        source_sha256={p.name:digest(p) for p in HERE.iterdir() if p.suffix in ('.py','.json','.sh')},
        generated_sha256={p.name:digest(p) for p in out.iterdir() if p.suffix in ('.cpp','.hpp','.inc')})
    (out/'result.json').write_bytes((json.dumps(report,indent=2)+'\n').encode())
    print('SRAM_PORT_COMPARE_PASS '+str(len(records)),flush=True)


if __name__=='__main__':main()
