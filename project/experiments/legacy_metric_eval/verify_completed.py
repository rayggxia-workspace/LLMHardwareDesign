"""Independent read-only audit of the21-case historical evaluation matrix.

This preserves the old S32/S96 architecture assumptions. It never treats the
native_serial study or the implemented four1RW-bank RTL as an ideal1R1W port.
API: verify_completed(report, refs) -> dict; refs values may be loaded dicts or
original JSON paths. The caller must SHA-gate original bytes for loaded dicts.
"""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path

BEST='adaptive_prefix_pair_combine'
WORKLOADS=(('decode512','queued_pipe_w8',BEST),('decode512','queued_pipe_w16','adaptive'),
           ('decode2048','queued_pipe_w8',BEST),('prefill2','queued_pipe_w8',BEST))
ARCHIVES={
 '9015effa13879bf8b5779905a4c83f53af8f2085':'62c787396bd331cb2c6d8a0a4352a4ebb83456616eb141bc50c33655d84f3fc3',
 '45e45bf75f35ebf35111f525de655076f7e122be':'5c5e4c02084b1cc76be8f1b92fbbe5bde32fe538bb3a43a6fa94f240552507f9',
 'c597a7d0f7e5ee03100cea5d4ac65dd22cb93a11':'966729e962ecde76f755a9da873f3fb7ac566e4dd454f45e7d4b6f8f76c73cce',
 '49b3938ce8b55734520c56a79a7d5d7933af9cdc':'4dcb0f01357e2f71fcf9f90deeab1d1dd50101b3d928b3e9866473c91c133777',
 'e2b8c9f98b9c14a2d016062e77fcb094640e8dcc':'e8c72c436d52969f35eb6c623b8fbedbcdbd48d35c8a4fc69f5cc2ad94ec6c41',
}
TRACE_SHA={
 'decode512':'6ed2129e2f13842dc53b4ba2135ea41886d1c126d842661dc7d5ac38ffb26f1d',
 'decode2048':'ba4157469188fbc1602e3324fa747847d78d39e392c4674cf92d9aabbce9339f',
 'prefill2':'be2f0c96b7042674680a3ee51d99389a89813318034c29098cdb344d131441b7',
}


def require(ok,message):
    if not ok:raise ValueError(message)


def key(record):
    row=record['result'];hw=row.get('hardware_study',{});ctx=row.get('context_study',{})
    policy=row.get('policy_study',{});contract=record.get('contract',{})
    return (record['workload'],record.get('profile',row['profile']),record.get('variant',row['detail']['variant']),
            record.get('contexts',ctx.get('contexts',1)),record.get('switch_cycles',ctx.get('switch_cycles',1)),
            int(record.get('reuse_A',ctx.get('reuse_A',True))),record.get('P_KiB',hw.get('P_S_bytes',16384)//1024),
            int(record.get('dual_ports',hw.get('split_P_read_write_ports',contract.get('split_P_read_write_ports',False)))),
            record.get('P_port_quarters',4),record.get('policy_KiB',policy.get('requested_policy_KiB',0)))


def planned():
    result=[]
    for workload,profile,variant in WORKLOADS:
        for contexts in (1,8):
            for dual in (0,1):result.append((workload,profile,variant,contexts,1,1,16,dual,4,0))
    for workload in ('decode512','prefill2'):
        for kib in (48,64):result.append((workload,'queued_pipe_w8',BEST,1,1,1,kib,1,4,16))
    result.append(('decode512','queued_pipe_w8','observe',1,1,1,16,0,4,0))
    return tuple(result)


def historical_projection(actual,reference,path=()):
    """Every old field is exact. Only known subsequently added metadata differs."""
    if isinstance(reference,dict):
        require(isinstance(actual,dict),'historical dict type '+str(path))
        extra=set(actual)-set(reference)
        allowed={'hardware_study','compare_study','policy_study'} if not path else (
            {'P_capacity_bytes','P_service_cycles'} if path==('detail',) else set())
        require(extra<=allowed,'unexpected added historical fields '+str(path)+str(extra-allowed))
        for name,value in reference.items():
            require(name in actual,'missing original historical field '+str(path+(name,)))
            historical_projection(actual[name],value,path+(name,))
    elif isinstance(reference,list):
        require(isinstance(actual,list) and len(actual)==len(reference),'historical list length '+str(path))
        for index,value in enumerate(reference):historical_projection(actual[index],value,path+(index,))
    else:require(actual==reference,'historical value differs '+str(path))


def budget(record):
    workload,profile,variant,contexts,switch,reuse,kib,dual,quarters,policy=key(record)
    row=record['result'];hw=row['hardware_study'];port=row['compare_study'];context=row['context_study'];p=row['policy_study'];detail=row['detail']
    require(key(record) in planned(),'case outside frozen21-case plan')
    require(row['profile']==profile and detail['variant']==variant,'profile/variant metadata mismatch')
    for name,value in dict(P_count=2,P_S_bytes=kib*1024,U_S_bytes=16384,total_private_S_bytes=(2*kib+16)*1024,
                           aggregate_bandwidth_B_s=17100000000,S_port_bytes=64,S_port_cycles=1,DDR_beat_bytes=64,
                           split_P_read_write_ports=bool(dual),vector_lanes=4).items():
        require(hw.get(name)==value,'old hardware budget '+name)
    for name,value in dict(P_capacity_bytes=kib*1024,P_port_quarter_cycles=4,P_port_subcycles=1000,P_count=2,
                           U_capacity_bytes=16384,U_port_subcycles=1000,dual_ports=bool(dual)).items():
        require(port.get(name)==value,'old port/capacity budget '+name)
    require(p['requested_policy_KiB']==policy and p['effective_policy_bytes']==(policy or kib)*1024 and
            p['actual_P_capacity_bytes']==kib*1024,'policy-only reference confused with real capacity')
    require(context['contexts']==contexts and context['switch_cycles']==1 and context['reuse_A'] is True,'context configuration')
    require(len(context['P'])==2 and len(hw['P_ports'])==2,'P state count')
    for worker,state in enumerate(context['P']):
        require(state['worker']==worker and state['psum_register_bytes_peak']<=contexts*8*12,'S96 context finite payload')
        require(state['switch_subcycles']==state['context_switches']*1000,'context switch1 charged per virtual command')
        require(state['A_bank_peak']<=2 and state['B_bank_peak']<=2,'finite A/B token capacity')
    for worker,state in enumerate(hw['P_ports']):
        require(state['worker']==worker and state['DDR_channel']==worker,'old P/channel assignment')
        calendar=detail['S_calendars'][worker]
        for new,old in (('read_or_unified_service_subcycles','service_subcycles'),
                        ('read_or_unified_wait_subcycles','scheduled_wait_subcycles'),
                        ('read_or_unified_reservations','reservations')):
            require(state[new]==calendar[old],'added P port metadata differs from original detail '+new)
        if not dual:
            require(all(state[k]==0 for k in ('write_service_subcycles','write_wait_subcycles','write_reservations')),
                    'shared port silently gained independent write service')
        else:require(state['write_service_subcycles']>0 and state['write_reservations']>0,'ideal-port target missing paid write service')
    require(detail['P_capacity_bytes']==kib*1024 and detail['P_service_cycles']==1,'detail S contract')
    require(row['P_scratch_peak_bytes']<=kib*1024 and row['U_cache_peak_bytes']+4096<=16384,'P/U capacity')
    require(all(row[n]<=32 for n in ('max_outstanding_beats','max_descriptor_queue','max_outstanding_descriptors')),'finite DDR credits')
    require(detail['subcycles_per_core_cycle']==1000,'subcycle/core cycle confusion')
    end=detail['end_subcycles'];tokens=2 if workload=='prefill2' else 1
    require(end>0 and row['tokens']==tokens and row['ticks']==(end+999)//1000,'old endpoint/token count')
    expected_rate=tokens*300000000*1000/end
    require(math.isfinite(row['tokens_per_second']) and math.isclose(row['tokens_per_second'],expected_rate,rel_tol=2e-10),
            'old300MHz throughput arithmetic')
    require(math.isclose(row['seconds'],end/300000000/1000,rel_tol=2e-10),'old reference clock changed')
    require('conditional_tokens_per_second' not in row and 'native_study' not in row,'native_serial basis leaked into historical evaluation')
    u=detail['S_calendars'][3]
    require(hw['U_service_subcycles']==u['service_subcycles'] and hw['U_wait_subcycles']==u['scheduled_wait_subcycles'] and
            hw['U_reservations']==u['reservations'],'U local work metadata')
    layer=('unimplemented_capacity_reference' if kib>16 else 'ideal_independent_port_target_reference' if dual else
           'shared_port_context_direction_projection' if contexts==8 else 'old_optimized_reference' if variant==BEST else 'old_reference')
    return dict(layer=layer,private_S_total_bytes=(2*kib+16)*1024,
                projected_S96_context_payload_bytes_per_P=contexts*96,
                extra_S96_payload_vs_one_context_bytes_per_P=(contexts-1)*96,
                tokens_per_second=row['tokens_per_second'],physical_or_native_qualified=False)


def load_references(refs):
    require(isinstance(refs,dict) and refs,'missing original reference reports')
    reports={};provenance={}
    for label,value in refs.items():
        if isinstance(value,dict):
            report=value;digest=None
        else:
            path=Path(value);raw=path.read_bytes();report=json.loads(raw);digest=hashlib.sha256(raw).hexdigest()
        commit=report.get('source_commit')
        require(report.get('passed') is True and commit in ARCHIVES,'unrecognized/failed historical receipt '+label)
        if digest:require(digest==ARCHIVES[commit],'original reference file SHA drift '+label)
        provenance[label]=dict(source_commit=commit,expected_original_sha256=ARCHIVES[commit],
                               original_file_SHA_verified_here=bool(digest))
        reports[label]=report
    return reports,provenance


def verify_completed(report,refs):
    # The runner calls this before promoting its final passed flag. Any
    # recorded execution error still fails; success is established below.
    require(not any(report.get(k) for k in ('errors','error','traceback')),'evaluation contains execution errors')
    records=report.get('cases',[]);counts=Counter(key(r) for r in records)
    require(len(records)==21 and counts==Counter(planned()),'missing/duplicate/wrong21-case factorial')
    references,provenance=load_references(refs);index={}
    require(report.get('run12_generated_exact') is True,'frozen run12 generator equality not established')
    run12=[r for r in references.values() if r.get('source_commit')=='e2b8c9f98b9c14a2d016062e77fcb094640e8dcc']
    require(len(run12)==1 and report.get('generated_sha256')==run12[0]['legacy']['generated_sha256'],
            'generated five-file model differs from run12')
    for label,digest in report.get('prior_sha256',{}).items():
        require(label in provenance and digest==provenance[label]['expected_original_sha256'],'reference raw SHA metadata '+label)
    for label,archive in references.items():
        body=archive.get('legacy',archive)
        for record in body.get('cases',[]):
            hw=record['result'].get('hardware_study',record.get('contract',{}))
            if hw.get('P_count',2)!=2 or hw.get('vector_lanes',4)!=4:continue
            k=key(record)
            index.setdefault(k,[]).append((label,record['result']))
    verified=[]
    for record in records:
        k=key(record);checks=budget(record);matches=[]
        for label,old in index.get(k,[]):
            historical_projection(record['result'],old);matches.append(label)
        require(matches,'not previously observed: missing historical whole-result reference '+str(k))
        verified.append(dict(key=list(k),historical_whole_fields_exact=matches,**checks))
    # In each capacity16 factorial, scalar/native-S32 work and B/output bytes
    # are fixed; context changes may save A. Port changes alone save no bytes.
    bykey={key(r):r['result'] for r in records}
    def flows(row,name):
        total=Counter()
        for channel in row['detail']['channels']:total.update(channel['flows'][name])
        return dict(total)
    for workload,profile,variant in WORKLOADS:
        rows={(ctx,dual):bykey[(workload,profile,variant,ctx,1,1,16,dual,4,0)] for ctx in (1,8) for dual in (0,1)}
        base=rows[1,0]
        for row in rows.values():
            for field in ('tokens','M_commands','M_work_ticks','vector_work_ticks','KV_state_write_bytes'):
                require(row[field]==base[field],'factorial work changed '+field)
            for name in ('weight','dynamic_B','dot_output'):require(flows(row,name)==flows(base,name),'factorial B/output work changed '+name)
            require(row['hardware_study']['U_service_subcycles']==base['hardware_study']['U_service_subcycles'],'factorial U work changed')
        for ctx in (1,8):
            for field in ('read_bus_bytes','write_bus_bytes','logical_read_bytes','logical_write_bytes','dma_descriptors'):
                require(rows[ctx,0][field]==rows[ctx,1][field],'ideal port silently removed data '+field)
        for dual in (0,1):
            require(flows(rows[8,dual],'A')['logical_read']<=flows(rows[1,dual],'A')['logical_read'],'context A work grew')
    return dict(passed=True,cases=21,reference_receipts=provenance,cases_verified=verified,
                layers=dict(shared_port_context_direction='historical S32/S96 mechanism projection',
                            ideal_independent_port='target reference, not mathematical bound or implemented1RW capability',
                            larger_capacity='48/64KiB candidate reference only; SRAM expansion not implemented'),
                native_serial_used_as_basis=False,implemented_RTL_token_rate_claimed=False,
                scope='old-metric exact historical replay and resource/work audit; no simulation or physical qualification')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--result',type=Path,required=True);p.add_argument('--ref',action='append',required=True,metavar='LABEL=JSON')
    p.add_argument('--out',type=Path);a=p.parse_args();refs=dict(item.split('=',1) for item in a.ref)
    completed=json.loads(a.result.read_text(encoding='utf-8'))
    require(completed.get('passed') is True,'standalone verification requires a completed passed report')
    result=verify_completed(completed,refs)
    text=json.dumps(result,indent=2)+'\n'
    if a.out:a.out.write_text(text,encoding='utf-8')
    print(text,end='')
