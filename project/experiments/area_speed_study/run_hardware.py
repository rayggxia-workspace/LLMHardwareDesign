"""Stages 3->4->5, gated on actual passed stage1 and elastic-RTL receipts."""
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

from generate_hardware import generate_hardware,verify_sources,HERE,BASE
from audit import check as legacy_check,trace_info


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def execute(command,log,cwd,env=None):
    process=subprocess.run(list(map(str,command)),cwd=cwd,env=env,
                           stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    log.write_bytes(process.stdout)
    if process.returncode:raise RuntimeError(str(command)+' '+process.stdout.decode(errors='replace')[-3000:])
    return process.stdout.decode()


def gate(receipt,name):
    if receipt.get('passed') is not True or not isinstance(receipt.get('source_commit'),str) or not receipt['source_commit']:
        raise ValueError(name+' has no actual passed/source_commit receipt')


def audit(row,trace,baseline,contract,contexts,switch,reuse):
    pcount,dual,lanes=contract
    result=legacy_check(row,trace)
    tensors,ops,_=trace_info(trace)
    h=row['hardware_study'];d=row['detail'];c=row['context_study']
    assert h['P_count']==pcount and h['P_S_bytes']==16384 and h['U_S_bytes']==16384
    assert h['total_private_S_bytes']==(pcount+1)*16384
    assert h['split_P_read_write_ports']==dual and h['vector_lanes']==lanes
    assert h['aggregate_bandwidth_B_s']==17100000000
    assert h['S_port_bytes']==64 and h['S_port_cycles']==1 and h['DDR_beat_bytes']==64
    assert c['contexts']==contexts and c['switch_cycles']==switch and c['reuse_A']==bool(reuse)
    assert len(h['P_ports'])==pcount and len(d['P'])==pcount and len(c['P'])==pcount
    for name in ('M_commands','M_tiles','M_work_ticks','adapter_work_ticks'):
        assert row[name]==baseline[name],name
    if lanes==4:assert row['vector_work_ticks']==baseline['vector_work_ticks']
    else:assert row['vector_work_ticks']<=baseline['vector_work_ticks']
    assert h['U_service_subcycles']==d['S_calendars'][3]['service_subcycles']
    assert h['U_wait_subcycles']==d['S_calendars'][3]['scheduled_wait_subcycles']
    assert h['U_reservations']==d['S_calendars'][3]['reservations']
    assert h['U_service_subcycles']==baseline['detail']['S_calendars'][3]['service_subcycles']
    write_total=0
    for worker,port in enumerate(h['P_ports']):
        assert port['worker']==worker and port['DDR_channel']==(0 if worker in (0,2) else 1)
        cal=d['S_calendars'][worker]
        assert port['read_or_unified_service_subcycles']==cal['service_subcycles']
        assert port['read_or_unified_wait_subcycles']==cal['scheduled_wait_subcycles']
        assert port['read_or_unified_reservations']==cal['reservations']
        assert port['write_service_subcycles']<=d['end_subcycles']
        write_total+=port['write_service_subcycles']
        if not dual:
            assert port['write_service_subcycles']==port['write_wait_subcycles']==port['write_reservations']==0
    flows=result['flow_totals']
    if dual:
        p_input=sum(flows[name]['bus_read'] for name in ('A','weight','dynamic_B'))
        m_output_beats=m_output_events=0
        for op in ops:
            if op['kind']!='Dot':continue
            for rr in range(0,op['r'],8):
                for col in range(0,op['n'],8):
                    m_output_beats+=((min(8,op['r']-rr)*min(8,op['n']-col)*4+63)//64)*op['batches']
                    m_output_events+=op['batches']
        assert write_total==(p_input//64+m_output_beats)*1000,'separate P input/M-result write service conservation'
        assert sum(p['write_reservations'] for p in h['P_ports'])==p_input//64+m_output_events
    if pcount==2:
        assert sum(p['read_or_unified_service_subcycles'] for p in h['P_ports'])+write_total==sum(
            p['service_subcycles'] for p in baseline['detail']['S_calendars'][:2]),'P S work must not disappear'
        assert sum(p['read_or_unified_reservations']+p['write_reservations'] for p in h['P_ports'])==sum(
            p['reservations'] for p in baseline['detail']['S_calendars'][:2]),'P S reservations must not disappear'
    if pcount==2:
        for key in ('read_bus_bytes','write_bus_bytes','logical_read_bytes','logical_write_bytes','dma_descriptors'):
            assert row[key]==baseline[key],key
    for channel in d['channels']:
        assert channel['row_misses']<=channel['beats']
        assert channel['direction_changes']<=channel['beats']
    # Independently count enabled calls and context/A groups for arbitrary P
    # count. The ordinary shape/weight/MAC checks above remain independent.
    expected=[dict(enabled_calls=0,groups=0,A_groups=0,A_loaded_bytes=0,A_saved_bytes=0,
                   context_switches=0,switch_subcycles=0,psum_register_bytes_peak=0,completed_contexts=0)
              for _ in range(pcount)]
    weight_bits=8 if 'w8' in row['profile'] else 16
    pairs='pair' in row['detail']['variant'];prefix='prefix' in row['detail']['variant']
    workspace=1024+(512 if 'combine' in row['detail']['variant'] else 0)
    for op in ops:
        if contexts==1 or op['kind']!='Dot' or op['r']!=1 or op['layout']!=0:continue
        bits=tensors[op['inputs'][0]][2];full_A=op['k']*(bits//8)
        minimum_b=2*((8*8*(weight_bits//8)+63)//64*64)
        if full_A+minimum_b+96+workspace<=16384:continue
        chunks=(op['k']+255)//256
        fixed=2*(((256*(bits//8)+63)//64*64)+((8*256*(weight_bits//8)+63)//64*64))+128+workspace
        cache_k=min(op['k'],((16384-fixed)//(bits//8)//256)*256) if prefix and fixed<16384 else 0
        cached=cache_k*(bits//8)
        for worker,e in enumerate(expected):
            columns=[col for col in range(0,op['n'],8)
                     if ((col//16)%pcount if pairs else (col//8)%pcount)==worker]
            count=len(columns);groups=(count+contexts-1)//contexts;batches=op['batches']
            e['enabled_calls']+=1;e['groups']+=groups*batches
            e['A_groups']+=chunks*(groups if reuse else count)*batches
            e['A_loaded_bytes']+=((cached if count else 0)+(full_A-cached)*(groups if reuse else count))*batches
            if reuse:e['A_saved_bytes']+=(full_A-cached)*(count-groups)*batches
            e['context_switches']+=count*chunks*batches
            e['switch_subcycles']+=count*chunks*batches*switch*1000
            e['psum_register_bytes_peak']=max(e['psum_register_bytes_peak'],min(count,contexts)*96)
            e['completed_contexts']+=count*batches
    for worker,e in enumerate(expected):
        actual=c['P'][worker]
        for key,value in e.items():assert actual[key]==value,(worker,key,actual[key],value)
        assert actual['A_bank_peak']<=2 and actual['B_bank_peak']<=2
    clean=deepcopy(row);del clean['hardware_study']
    if contract==(2,False,4):assert clean==baseline,'default hardware changes complete stage1 result'
    return dict(passed=True,legacy=result,independent_context_counts=expected,
                P_input_write_service_subcycles=write_total,
                scope='capacity/work/traffic/stage/port conservation; conditional architecture, no physical qualification')


def main():
    parser=argparse.ArgumentParser()
    for name in ('inputs','out','stage1','stage2'):parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();out=args.out.resolve();inputs=args.inputs.resolve()
    # Do not create outputs or build/run anything until both prerequisite gates
    # are truly passed. Record their actual files, SHA and source commits.
    stage1=json.loads(args.stage1.read_text(encoding='utf-8'));stage2=json.loads(args.stage2.read_text(encoding='utf-8'))
    gate(stage1,'stage1');gate(stage2,'stage2')
    lock=verify_sources()
    for name,value in lock['hardware_base_sha256'].items():
        assert stage1['source_sha256'][name]==value,'stage1 source receipt mismatch '+name
    for name,value in lock['input_sha256'].items():assert digest(inputs/name)==value,name
    out.mkdir(parents=True,exist_ok=False);(out/'generated').mkdir()
    (out/'m-profile.log').write_bytes((inputs/'m-profile.log').read_bytes())
    prefix=Path('/public/home/yuzelu/opt/systemc-3.0.2-issue219')
    flags=['-std=c++17','-O2','-Wall','-Wextra','-Werror']
    built={};workers=min(4,int(os.environ['SLURM_CPUS_PER_TASK']))
    if workers<1:raise ValueError('no allocated worker')
    def build(contract):
        if contract in built:return built[contract]
        pcount,dual,lanes=contract;name=f'p{pcount}-rw{int(dual)}-v{lanes}'
        folder=out/name;folder.mkdir();generate_hardware(folder,pcount,dual,lanes)
        execute(['g++',*flags,folder/'model.cpp','-I'+str(folder),'-I'+str(prefix/'include'),
                 '-L'+str(prefix/'lib'),'-Wl,-rpath,'+str(prefix/'lib'),'-lsystemc','-o',folder/'model'],
                folder/'build.log',out)
        built[contract]=folder/'model';return folder/'model'
    def baseline_for(workload,profile,variant,contexts,switch=1):
        return next(case['result'] for case in stage1['cases'] if case['workload']==workload and
                    case['profile']==profile and case['variant']==variant and case['contexts']==contexts and
                    case['switch_cycles']==switch and case['reuse_A'])
    records=[]
    def case(stage,contract,item):
        workload,profile,variant,contexts,switch=item;binary=build(contract)
        name=f'{stage}-{workload}-{profile}-{variant}-c{contexts}-s{switch}-{binary.parent.name}'
        text=execute([binary,inputs/(workload+'.trace'),profile,variant,contexts,switch,1],out/(name+'.log'),out)
        assert 'MODEL_FAILURE' not in text and 'SystemC 3.0.2' in text
        rows=[json.loads(line[7:]) for line in text.splitlines() if line.startswith('RESULT ')];assert len(rows)==1
        row=rows[0];reference=baseline_for(workload,profile,variant,contexts,switch)
        checked=audit(row,inputs/(workload+'.trace'),reference,contract,contexts,switch,1)
        old_ctx1=baseline_for(workload,profile,variant,1)
        record=dict(stage=stage,contract=dict(P_count=contract[0],split_P_read_write_ports=contract[1],vector_lanes=contract[2]),
            workload=workload,profile=profile,variant=variant,contexts=contexts,switch_cycles=switch,reuse_A=True,
            result=row,audit=checked,speedup_vs_same_context=reference['seconds']/row['seconds'],
            speedup_vs_old_best_ctx1=old_ctx1['seconds']/row['seconds'],
            log_sha256=digest(out/(name+'.log')))
        (out/(name+'.json')).write_bytes((json.dumps(record,indent=2)+'\n').encode())
        print(json.dumps(dict(case=name,tokens_s=row['tokens_per_second'],
                             speedup_vs_old_best_ctx1=record['speedup_vs_old_best_ctx1'],
                             bus_bytes=row['read_bus_bytes']+row['write_bus_bytes'])),flush=True)
        return record
    core=[('decode512','queued_pipe_w8','adaptive_prefix_pair_combine',1,1),
          ('decode512','queued_pipe_w8','adaptive_prefix_pair_combine',8,1),
          ('decode512','queued_pipe_w16','adaptive',1,1)]
    switch3=('decode512','queued_pipe_w8','adaptive_prefix_pair_combine',8,3)
    default=(2,False,4);binary=build(default)
    execute(['g++',*flags,BASE/'upstream/kernel_probe.cpp','-o',out/'kernel_probe'],out/'kernel-build.log',out)
    env=dict(os.environ,BLOCK_STUDY_MODEL=str(binary))
    for script in ('check_kernels.py','validate.py','smoke.py'):
        execute([sys.executable,'-B',BASE/'upstream'/script],out/(script+'.log'),out,env)
    # Build once outside each parallel case batch; candidate build mutations and
    # stage transitions are sequential, never raced by worker threads.
    for stage,contracts in [('baseline',[default]),('stage3-P-1R1W',[(2,True,4)]),
                            ('stage4-third-P',[(3,False,4)]),('stage5-vector-lanes',[(2,False,8),(2,False,16)])]:
        for contract in contracts:
            build(contract)
            items=core+([switch3] if stage in ('baseline','stage3-P-1R1W') else [])
            with ThreadPoolExecutor(max_workers=workers) as pool:
                records+=list(pool.map(lambda item:case(stage,contract,item),items))
    choices=[record for record in records if record['workload']=='decode512' and
             record['profile']=='queued_pipe_w8' and record['contexts']==1]
    best=min(choices,key=lambda record:record['result']['seconds']);chosen=best['contract']
    best_contract=(chosen['P_count'],chosen['split_P_read_write_ports'],chosen['vector_lanes'])
    for contract in dict.fromkeys([default,best_contract]):
        build(contract)
        items=[(workload,'queued_pipe_w8','adaptive_prefix_pair_combine',1,1) for workload in ('decode2048','prefill2')]
        with ThreadPoolExecutor(max_workers=workers) as pool:
            records+=list(pool.map(lambda item:case('supplement',contract,item),items))
    # Refuse metadata that would silently advertise more hardware/bandwidth.
    sample=next(record for record in records if record['contract']['split_P_read_write_ports'])
    bad=deepcopy(sample['result']);bad['hardware_study']['P_ports'][0]['write_service_subcycles']+=1
    try:audit(bad,inputs/'decode512.trace',baseline_for('decode512','queued_pipe_w8','adaptive_prefix_pair_combine',1),(2,True,4),1,1,1)
    except AssertionError:negative_write_port=True
    else:raise ValueError('hidden write-port service accepted')
    for name,value in [('stage1',stage1),('stage2',stage2)]:
        bad=deepcopy(value);bad['passed']=False
        try:gate(bad,name)
        except ValueError:pass
        else:raise ValueError('failed prerequisite accepted')
    report=dict(passed=True,issue=247,source_commit=json.loads((out.parent/'inputs.json').read_text(encoding='utf-8'))['source_commit'],
        stage_order=['baseline','stage3-P-1R1W','stage4-third-P','stage5-vector-lanes','supplement'],
        scope='conditional extra hardware; each P/U keeps 16KiB, third P adds one private S; no physical/DDR/numeric/energy qualification',
        prerequisite_receipts={name:dict(source_commit=receipt['source_commit'],sha256=digest(path))
                               for name,receipt,path in [('stage1',stage1,args.stage1),('stage2',stage2,args.stage2)]},
        versions=dict(python=platform.python_version(),SystemC='3.0.2',gcc=subprocess.check_output(['g++','--version'],text=True).splitlines()[0]),
        baseline_complete_stage1_exact=True,negative_checks=dict(write_port_service=negative_write_port,failed_prerequisites=2),
        selected_context1_contract=chosen,cases=records,input_sha256=lock['input_sha256'],
        source_sha256={p.name:digest(p) for p in HERE.iterdir() if p.suffix in ('.py','.json','.sh','.hpp','.inc')},
        generated_sha256={str(p.relative_to(out)):digest(p) for p in out.rglob('*') if p.suffix in ('.cpp','.hpp','.inc')})
    (out/'result.json').write_bytes((json.dumps(report,indent=2)+'\n').encode())
    print('AREA_HARDWARE_PASS '+str(len(records)),flush=True)


if __name__=='__main__':main()
