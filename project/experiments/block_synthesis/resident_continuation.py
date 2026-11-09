"""Construct finite, state-closed resident loops without assuming a warm SRAM.

Only loop-invariant read-only records, proven guard words, and an identified
M B bank may survive. Every other SSA record is fresh in the next element.
The deterministic allocation policy can have a transient and a cycle; all
transient iterations are charged, not approximated by one steady-state cost.
"""
import json

from resident_records import plan


def invariants(graph,loop):
    return sorted(key for key,o in graph['objects'].items() if o['kind']=='constant' or
                  o['kind']=='external' and loop['sources'].get(o['tensor'])=='scalar')


def compile_loop(graph,loop,actors,zero_address,*,max_programs=256,**options):
    count=loop['elements']
    if type(count)!=int or count<1 or type(max_programs)!=int or max_programs<1:
        raise ValueError('positive resident loop extent/program limit required')
    persistent=invariants(graph,loop);programs=[];seen={};seed=None;cycle=None
    while len(programs)<count:
        key=json.dumps(seed,sort_keys=True,separators=(',',':'))
        if key in seen:
            cycle=seen[key];break
        if len(programs)>=max_programs:
            raise ValueError('resident continuation did not close within the declared search limit')
        seen[key]=len(programs)
        body=plan(graph,actors,zero_address,persistent=persistent,initial=seed,**options)
        if body['status']!='planned':raise ValueError('resident continuation has no legal finite-S program')
        programs.append(body);seed=body['continuation']
    result={'kind':'readonly-resident-loop-v1','elements':count,'persistent_records':persistent,
            'programs':programs,'cycle_start':cycle,
            'scope':'serial cold/transient/cyclic event programs; read-only SRAM/guards/B bank only; no inter-element arithmetic state or free transport'}
    # These totals are checked independently from the emitted sequence.
    result['totals']=totals(result)
    return result


def program_index(sequence,index):
    count=sequence['elements'];programs=sequence['programs'];start=sequence['cycle_start']
    if type(index)!=int or not 0<=index<count:raise ValueError('resident continuation element outside extent')
    if index<len(programs):return index
    if start is None:raise ValueError('resident continuation sequence is truncated')
    return start+(index-start)%(len(programs)-start)


def visits(sequence):
    count=sequence['elements'];size=len(sequence['programs']);start=sequence['cycle_start']
    result=[int(i<count) for i in range(size)]
    if count>size:
        if start is None or not 0<=start<size:raise ValueError('resident continuation cycle required')
        turns,tail=divmod(count-size,size-start)
        for i in range(start,size):result[i]+=turns+int(i-start<tail)
    return result


def totals(sequence):
    return {field:sum(n*p[field] for n,p in zip(visits(sequence),sequence['programs']))
            for field in ('copy_ticks','native_service_ticks','total_ticks',
                          'external_load_words','external_store_words','external_words')}
