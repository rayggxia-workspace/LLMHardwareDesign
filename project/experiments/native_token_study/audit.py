"""Independent trace-derived work/space audit; never imports the timing model.

Public API: check(result, trace_path, profile), check_pair(before, after, trace).
Only arithmetic/traffic/lifetime budgets are audited here. RTL timing is gated
separately against run13; a conditional throughput is not native generation.
"""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path


def need(ok,message):
    if not ok:raise ValueError(message)


def ceildiv(a,b):return (a+b-1)//b


def read_trace(path):
    path=Path(path);raw=path.read_bytes();it=iter(raw.decode('utf-8').split())
    nt,no,tokens=(int(next(it)) for _ in range(3));need(nt>0 and no>=0 and tokens>0,'trace header')
    tensors=[]
    for index in range(nt):
        tid,elements,bits,initial=(int(next(it)) for _ in range(4))
        # A 64-bit inventory/control tensor exists in prefill. It is not an M
        # operand; admission below is checked independently at each Dot.
        need(tid==index and elements>=0 and bits in (8,16,32,64),'unsupported trace tensor')
        tensors.append(dict(elements=elements,bits=bits,initial=initial))
    ops=[]
    for _ in range(no):
        out=int(next(it));kind=next(it)
        elements,rows,cols,k,batches,shift,layout,n=(int(next(it)) for _ in range(8))
        inputs=[int(next(it)) for _ in range(n)]
        need(0<=out<nt and all(0<=x<out for x in inputs),'trace topology')
        ops.append(dict(out=out,kind=kind,elements=elements,rows=rows,cols=cols,k=k,batches=batches,
                        shift=shift,layout=layout,inputs=inputs))
    need(next(it,None) is None,'trace trailing fields')
    return tensors,ops,tokens,hashlib.sha256(raw).hexdigest()


def expected(tensors,ops,context,contexts,weight_bits):
    """Closed-form totals by logical matrix shape, not a replay of worker waits."""
    fields=('dma_input_words dma_output_words local_read_words local_write_words wide_reads A_beats B_beats loads B_only_loads '
            'packed_A_bytes packed_B_bytes raw_A_conversion_read_bytes raw_B_conversion_read_bytes split_cycles merge_cycles final_rne_cycles '
            'scale_commands MAC_commands raw_commands RNE_commands release_commands static_groups dynamic_groups context_groups context_outputs '
            'S96_terms S96_clear_words resident_A_bytes peak_S_bytes useful_MACs static_S32_MAC_commands dynamic_MAC_commands '
            'scalar_row_terms S8_bitpass_issues source_A_DDR_bytes source_B_DDR_bytes output_DDR_bytes').split()
    totals=[Counter({k:0 for k in fields}) for _ in range(2)];flow=Counter();slot_peak=[0,0]
    matrix=[o for o in ops if o['kind']=='Dot']
    for o in matrix:
        need(len(o['inputs'])==2 and min(o['rows'],o['cols'],o['k'],o['batches'])>0,'invalid Dot shape')
        a=tensors[o['inputs'][0]];b=tensors[o['inputs'][1]];static=o['layout']==0
        need(a['bits'] in (8,16,32) and b['bits'] in (8,16,32),'64bit/control tensor cannot enter native Dot')
        abits=a['bits'];bbits=weight_bits if static else b['bits'];abytes=abits//8;bbytes=bbits//8
        need(o['layout'] in (0,1,2),'unsupported Dot layout')
        la=3 if abits==32 else 1;lb=3 if bbits==32 else 1
        inner=(1 if abits==8 else 3)*(1 if bbits==8 else 3)
        k=o['k'];chunks=ceildiv(k,32);tiles=ceildiv(k,8);last=k-32*(chunks-1)
        pieces=((32,chunks-1),(last,1));copies=o['rows']*o['batches'];frames=1 if bbits==8 else 2
        use_context=context and static and o['rows']==1 and la*k<=65535
        grouping=contexts if use_context else 1
        fixed=1024+32*8*bbytes+4*64*frames*lb+4*64*(1 if static else la)+96+32+32
        raw_a=k*abytes;resident=raw_a+fixed<=16384;peak=fixed+(raw_a if resident else 32*abytes)
        need(peak<=16384,'derived16KiB overflow')
        a_read_words=sum(repeat*ceildiv(length*abytes,16) for length,repeat in pieces)
        for worker,s in enumerate(totals):
            s['peak_S_bytes']=max(s['peak_S_bytes'],peak)
            columns=Counter(min(8,o['cols']-col) for col in range(worker*8,o['cols'],16));q=sum(columns.values())
            if not q:continue
            groups=ceildiv(q,grouping);outs=q*copies;conversions=groups*copies;ext_outputs=0
            source_a=raw_a*(1 if resident else groups)*copies
            s['source_A_DDR_bytes']+=source_a;flow['A']+=source_a
            s['resident_A_bytes']+=raw_a*copies if resident else 0
            s['dma_input_words']+=(ceildiv(raw_a,16) if resident else groups*a_read_words)*copies
            s['raw_A_conversion_read_bytes']+=raw_a*conversions
            s['local_read_words']+=a_read_words*conversions
            packed_a=64*tiles*(1 if static else la)*conversions
            s['packed_A_bytes']+=packed_a;s['local_write_words']+=packed_a//16
            s['split_cycles']+=ceildiv(k,4)*conversions
            s['static_groups' if static else 'dynamic_groups']+=groups*copies
            s['context_groups']+=groups*copies if use_context else 0
            s['context_outputs']+=outs if use_context else 0
            if use_context:slot_peak[worker]=max(slot_peak[worker],min(contexts,q))
            # B work depends on its valid N tail; it is never reduced by A reuse.
            for n,amount in columns.items():
                count=amount*copies;raw_b=k*n*bbytes
                s['source_B_DDR_bytes']+=raw_b*count;flow['weight' if static else 'dynamic_B']+=raw_b*count
                s['raw_B_conversion_read_bytes']+=raw_b*count
                s['local_read_words']+=sum(repeat*ceildiv(length*n*bbytes,16) for length,repeat in pieces)*count
                if static:input_words=sum(repeat*ceildiv(length*n*bbytes,16) for length,repeat in pieces)
                elif o['layout']==1:input_words=n*sum(repeat*ceildiv(length*bbytes,16) for length,repeat in pieces)
                else:input_words=k*ceildiv(n*bbytes,16)
                s['dma_input_words']+=input_words*count
                packed_b=64*frames*lb*tiles*count
                s['packed_B_bytes']+=packed_b;s['local_write_words']+=packed_b//16
                s['split_cycles']+=ceildiv(k*n,4)*count
                s['output_DDR_bytes']+=n*4*count;flow['dot_output']+=n*4*count
                s['dma_output_words']+=ceildiv(n*4,16)*count;s['useful_MACs']+=k*n*count
            s['scale_commands']+=outs*chunks*la if use_context else groups*copies
            if static:
                s['loads']+=outs*chunks;s['B_only_loads']+=(q-groups)*chunks*copies if use_context else 0
                s['wide_reads']+=tiles*(groups+q*frames)*copies
                s['A_beats']+=la*tiles*groups*copies;s['B_beats']+=frames*tiles*outs
                mac=outs*chunks*(la if use_context else 1)
                s['MAC_commands']+=mac;s['static_S32_MAC_commands']+=mac if abits==32 else 0
                s['scalar_row_terms']+=outs*chunks*la;s['S8_bitpass_issues']+=outs*tiles*la*inner
                if use_context or la==1:s['RNE_commands']+=2*outs
                else:s['S96_terms']+=la*outs;s['S96_clear_words']+=6*outs;ext_outputs=outs
                if use_context:s['release_commands']+=outs
            else:
                terms=la*lb*chunks*outs
                s['MAC_commands']+=terms;s['dynamic_MAC_commands']+=terms
                s['scalar_row_terms']+=terms;s['S8_bitpass_issues']+=outs*tiles*la*lb*inner
                s['loads']+=terms;s['wide_reads']+=outs*tiles*la*lb*(1+frames)
                s['A_beats']+=outs*tiles*la*lb;s['B_beats']+=outs*tiles*la*lb*frames
                s['S96_terms']+=terms;s['S96_clear_words']+=6*outs;ext_outputs=outs
            # Packed96 is eight12B lanes. A pair24B touches two16B words,
            # including shared neighbor bytes. All four pairs are charged.
            terms_here=(la*outs if static and not use_context and la>1 else 0) if static else la*lb*chunks*outs
            s['raw_commands']+=4*terms_here;s['merge_cycles']+=12*terms_here
            s['final_rne_cycles']+=12*ext_outputs
            s['local_read_words']+=8*terms_here+8*ext_outputs
            s['local_write_words']+=8*terms_here+(6*ext_outputs)+2*outs
    counts=dict(all_Dot_calls=len(matrix),non_Dot_candidate_ops=len(ops)-len(matrix),
                S32_Dot_calls=sum(any(tensors[t]['bits']==32 for t in o['inputs']) for o in matrix),
                S32_Dot_input_occurrences=sum(tensors[t]['bits']==32 for o in matrix for t in o['inputs']))
    return totals,flow,slot_peak,counts


def flow_totals(row,name):
    result=Counter()
    for channel in row['detail']['channels']:result.update(channel['flows'][name])
    return dict(result)


def check(result,trace_path,profile):
    tensors,ops,tokens,digest=read_trace(trace_path);row=result;study=row['native_study']
    need(row.get('profile')==profile,'profile differs from actual invocation')
    need('tokens_per_second' not in row and row.get('conditional_tokens_per_second',0)>0,'unqualified/missing throughput key')
    need(study['native_admitted'] is False,'S32 conditional graph claimed native admission')
    need(study['P_count']==2 and study['U_count']==1 and study['P_private_S_bytes']==16384 and study['physical_banks']==4 and
         study['ports_per_bank']=='1RW' and study['ordinary_word_bytes']==16,'native resource contract')
    need(study['clock_hz']==300000000 and study['aggregate_DDR_bytes_per_second']==17100000000,'unfrozen clock/DDR assumption')
    need(study['same_P_async_controller'] is False and study['consumer_priority_cycle_gain']==0 and study['independent_bank_cycle_gain']==0,
         'serial controller invented bank/policy speedup')
    context=study['native_context'];contexts=study['requested_contexts'];weight_bits=study['weight_bits']
    need(isinstance(context,bool) and contexts in (1,8) and weight_bits in (8,16),'invalid route/context/weight profile')
    expected_profile=f'native_ctx{contexts}_w{weight_bits}' if context else f'native_legacy_w{weight_bits}'
    need(profile==expected_profile,'profile/route contract mismatch')
    budgets=dict(native_existing_result_RF_bytes=512,native_existing_operand_partial_result_payload_bytes=2704,
                 conditional_conversion_tile_register_bytes=2560,conditional_DMA_register_bytes=128,
                 conditional_merge_register_bytes=24,extra_adapter_register_bytes_per_P=2712,
                 context_control_added_bits=325 if context else 0)
    for name,value in budgets.items():need(study.get(name)==value,'resource budget changed '+name)
    need(study['extra_adapter_register_bytes_per_P']==sum(study[k] for k in
         ('conditional_conversion_tile_register_bytes','conditional_DMA_register_bytes','conditional_merge_register_bytes')),
         'conditional adapter register sum')
    wanted,flows,slots,calls=expected(tensors,ops,context,contexts,weight_bits)
    need(len(study['P'])==2,'P count')
    for name,value in calls.items():need(study[name]==value,'trace op count '+name)
    for worker,(actual,predicted) in enumerate(zip(study['P'],wanted)):
        need(actual['worker']==worker,'worker identity')
        for name,value in predicted.items():need(actual.get(name)==value,f'P{worker} {name}: got {actual.get(name)}, expected {value}')
        commands=sum(actual[k] for k in ('scale_commands','MAC_commands','raw_commands','RNE_commands','release_commands'))
        need(actual['wrapper_control_cycles']==4*commands,'wrapper command cost was dropped')
        need(len(actual['bank_operations'])==4 and sum(actual['bank_operations'])==
             actual['dma_input_words']+actual['dma_output_words']+actual['local_read_words']+actual['local_write_words']+4*actual['wide_reads'],
             'physical bank operation conservation')
        # Native final op5 store is5 cycles after its already charged leaf+4
        # wrapper, versus6 for other ordinary128 transactions. Wide service
        # reserves physical issue once; loader wall latency is not added twice.
        narrow_words=sum(actual[k] for k in ('dma_input_words','dma_output_words','local_read_words','local_write_words'))
        service=(6*narrow_words-actual['RNE_commands']+actual['wide_reads'])*1000
        need(row['detail']['S_calendars'][worker]['service_subcycles']==service,'P S service physical accounting')
        need(actual['load_cycles']>=actual['wide_reads'],'loader wall shorter than physical issue')
        need(0<=actual['peak_S_bytes']<=16384 and slots[worker]<=8,'S/context capacity')
    for flow,logical in flows.items():
        field='logical_write' if flow=='dot_output' else 'logical_read'
        need(flow_totals(row,flow).get(field,0)==logical,'native flow/detail mismatch '+flow)
    need(row['tokens']==tokens and row['M_commands']==sum(p['MAC_commands'] for p in study['P']),'token/M command conservation')
    need(row['M_tiles']==row['M_commands'],'native tile/command accounting')
    need(row['M_work_ticks']==sum(p['leaf_cycles']-3*p['RNE_commands'] for p in study['P']),'native leaf work accounting')
    need(row['adapter_work_ticks']==sum(p['split_cycles']+p['merge_cycles']+p['final_rne_cycles'] for p in study['P']),
         'conditional conversion/merge/RNE work accounting')
    need(row['P_scratch_peak_bytes']==max(p['peak_S_bytes'] for p in study['P']),'reported scratch peak')
    for p in row['detail']['P']:
        need(sum(p[k] for k in ('consumer_ready_wait_subcycles','input_ACK_wait_subcycles','service_subcycles','output_subcycles'))==p['elapsed_subcycles'],
             'P wall stages do not sum')
    end=row['detail']['end_subcycles'];need(end>0 and row['ticks']==ceildiv(end,1000),'tick endpoint')
    rate=tokens*300000000*1000/end
    need(math.isfinite(row['conditional_tokens_per_second']) and math.isclose(row['conditional_tokens_per_second'],rate,rel_tol=2e-10),'throughput arithmetic')
    return dict(passed=True,profile=profile,trace_sha256=digest,tokens=tokens,Dot_calls=calls['all_Dot_calls'],
                verified_P_fields=len(wanted[0]),native_context_peak=slots,
                normalized_scalar_row_terms=sum(p['scalar_row_terms'] for p in wanted),
                useful_MACs=sum(p['useful_MACs'] for p in wanted),
                conditional_tokens_per_second=rate,native_complete_graph_qualified=False)


def check_pair(before,after,trace_path):
    old=check(before,trace_path,before['profile']);new=check(after,trace_path,after['profile'])
    a=before['native_study'];b=after['native_study'];need(a['weight_bits']==b['weight_bits'],'mixed weight profiles')
    for flow in ('weight','dynamic_B','dot_output'):need(flow_totals(before,flow)==flow_totals(after,flow),'peer flow changed '+flow)
    for name in ('vector_work_ticks','KV_state_write_bytes','cache_hits','cache_misses','dirty_evictions','dead_lines_discarded','U_cache_peak_bytes'):
        need(before[name]==after[name],'frozen U behavior changed '+name)
    conserved=('useful_MACs','scalar_row_terms','S8_bitpass_issues','source_B_DDR_bytes','output_DDR_bytes',
               'raw_B_conversion_read_bytes','packed_B_bytes','B_beats')
    for p,q in zip(a['P'],b['P']):
        for name in conserved:need(p[name]==q[name],'peer native work changed '+name)
        for name in ('source_A_DDR_bytes','packed_A_bytes','raw_A_conversion_read_bytes','A_beats'):
            need(q[name]<=p[name],'candidate A work unexpectedly increased '+name)
    return dict(passed=True,before=old['profile'],after=new['profile'],trace_sha256=old['trace_sha256'],
                source_B_and_output_exactly_conserved=True,scalar_work_exactly_conserved=True,
                before_conditional_tokens_per_second=old['conditional_tokens_per_second'],
                after_conditional_tokens_per_second=new['conditional_tokens_per_second'],
                speedup=new['conditional_tokens_per_second']/old['conditional_tokens_per_second'])


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--trace',type=Path,required=True);p.add_argument('--result',type=Path,required=True)
    p.add_argument('--profile',required=True);p.add_argument('--before',type=Path);p.add_argument('--out',type=Path)
    a=p.parse_args();row=json.loads(a.result.read_text(encoding='utf-8'));report=check(row,a.trace,a.profile)
    if a.before:report['pair']=check_pair(json.loads(a.before.read_text(encoding='utf-8')),row,a.trace)
    text=json.dumps(report,indent=2)+'\n'
    if a.out:a.out.write_text(text,encoding='utf-8')
    print(text,end='')
