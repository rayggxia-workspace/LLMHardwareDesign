"""Addressed full-S32 Add aggregation, after explicitly charged preparation.

One r-by-1 M context, real feeder reads and SRAM ACKs. No host packing or
extra arithmetic. This module does not yet register a complete compiler
binding; split32 work and inter-stage copies must be added by that binding.
"""
from collections import Counter
import json
from pathlib import Path

from memory import descriptor_ticks


def read_qualification(directory,log=None):
    from s32_add_probe import analyse
    directory=Path(directory);log=Path(log) if log else directory/'simulate-0.log'
    report=analyse(directory,log,emit=False)
    if json.loads((directory/'summary.json').read_text())!=report:raise ValueError('Add receipt differs')
    result={'kind':'native-s32-add-aggregate-v1','P':{},'feeder':{},
        'provenance':{k:report[k] for k in ('manifest_sha256','log_sha256')},
        'scope':'prepared components -> exact full sum -> canonical S32 external STORE; preparation charged separately'}
    for p in report['passive_profiles']:
        if p['boundary']=='p-command':
            key={(4,0):'scale',(10,0):'execute',(5,1):'final_store'}.get((p['op'],p['store']))
            if key is None:continue
            result['P'].setdefault(str(p['rows']),{})[key]=p['max']+1
        else:
            result['feeder'].setdefault(str(p['rows']),{})['reuse_b' if p['reuse_b'] else 'cold']=p['max']+1
    return result


def aggregate_cost(elements,inputs,tile_rows,qualification,memory,p_meta,*,signs=None):
    if qualification.get('kind')!='native-s32-add-aggregate-v1':raise ValueError('qualified Add service required')
    if any(type(x)!=int or x<1 for x in (elements,inputs,tile_rows)) or tile_rows>8:
        raise ValueError('invalid Add extent')
    if inputs>((1<<63)-1)//((1<<31)+131072):raise ValueError('Add intermediate S64 bound exceeded')
    if signs is not None and (len(signs)!=inputs or any(s not in (-1,1) for s in signs)):
        raise ValueError('native Add signs must be +1/-1')
    load=descriptor_ticks(memory,1,'load',p_meta['io_write_ticks'])
    store=descriptor_ticks(memory,1,'store',p_meta['io_read_ticks'])
    # These are real external LOADs. The unit constant and unused feeder
    # padding remain in S while a single finite row tile is accumulated.
    count=Counter(ticks=17*load,external_read_words=17,initial_zero_loads=16,unit_loads=1)
    peak=0
    for start in range(0,elements,tile_rows):
        r=min(tile_rows,elements-start);q=qualification['P'].get(str(r));f=qualification['feeder'].get(str(r))
        if q is None or f is None:raise ValueError('Add row/tail not qualified')
        commands=3*inputs
        count.update(ticks=commands*r*load+f['cold']+(commands-1)*f['reuse_b']+
            commands*(q['scale']+q['execute'])+r*(q['final_store']+store),
            external_read_words=commands*r,external_write_words=r,prepared_loads=commands*r,
            scales=commands,executes=commands,feeds=commands,cold_feeds=1,reuse_feeds=commands-1,
            final_reads=r,tiles=1)
        peak=max(peak,512+(r-1)*8+1)
    return {**count,'external_words':count['external_read_words']+count['external_write_words'],
        'P_words':peak,'prepared_tile_words':3*inputs*min(tile_rows,elements),
        'cost_model':'native-s32-add-aggregate-v1','preparation_included':False,
        'context':'one r-by-1 S64, complete all operands before final S32 read; final STORE ACK before reuse'}


def commands(elements,inputs,tile_rows,*,prepared_id='prepared',output_id='result',signs=None):
    """Literal debug program; each external record has an explicit identity.

    Complete compiler bindings must resolve these SSA/index tuples to actual
    regions. No unsized buffer is represented as private SRAM here.
    """
    signs=[1]*inputs if signs is None else signs
    if len(signs)!=inputs or any(s not in (-1,1) for s in signs):raise ValueError('native Add signs must be +1/-1')
    for address in list(range(8))+list(range(16,24)):
        yield {'op':'LOAD','source':('constant:0',0),'dst':address}
    yield {'op':'LOAD','source':('constant:1',0),'dst':16}
    for start in range(0,elements,tile_rows):
        r=min(tile_rows,elements-start)
        for operand in range(inputs):
            for part in range(3):
                for row in range(r):
                    yield {'op':'LOAD','source':(prepared_id,start+row,operand,part),'dst':row}
                first=operand==0 and part==0
                yield {'op':'FEED','rows':r,'a_base':0,'b_base':16,'reuse_b':not first,'tiles':1}
                yield {'op':'SCALE','factor':signs[operand],'shift':0 if part==0 else 16}
                yield {'op':'EXECUTE','rows':r,'columns':1,'last_k':1,'tiles':1,'clear':first}
        for row in range(r):
            address=512+row*8
            yield {'op':'READ_FINAL','row':row,'width':32,'shift':0,'dst':address}
            yield {'op':'STORE','src':address,'destination':(output_id,start+row),'wait_ack':True}


def replay(prepared,elements,inputs,tile_rows,capacity=1024,*,signs=None):
    """Literal records and feeder snapshots, not numpy sum of the source.

    `prepared` is external memory keyed by (row,operand,component). The native
    command program performs every required transfer; output remains dirty
    only between the real final SRAM write and its external STORE ACK.
    """
    from tile_replay import SRAM,signed16,final32
    s=SRAM(capacity);counts=Counter();out={};a=None;b=None;acc=None;scale=None
    for event in commands(elements,inputs,tile_rows,signs=signs):
        op=event['op']
        if op=='LOAD':
            source=event['source']
            if source[0].startswith('constant:'):word=int(source[0].split(':')[1]);counts['initial_zero_loads' if word==0 else 'unit_loads']+=1
            else:
                value=prepared[tuple(source[1:])]
                if not -32768<=value<=32767:raise ValueError('prepared component outside S16')
                word=value&65535;counts['prepared_loads']+=1
            s.write_ack(event['dst'],word);counts['external_read_words']+=1
        elif op=='FEED':
            # All actual padding is read, including the second B half. No
            # dependence on a reset-filled memory or an invented B context.
            for address in range(4*((event['rows']+3)//4)):s.read(address)
            a=[signed16(s.read(row)) for row in range(event['rows'])]
            if not event['reuse_b']:
                b=[signed16(s.read(16+j)) for j in range(8)]
                if b[1:]!=[0]*7:raise ValueError('Add B padding changed')
                counts['cold_feeds']+=1;counts['tiles']+=1
            else:
                if b is None:raise ValueError('reuse before B load')
                counts['reuse_feeds']+=1
            counts['feeds']+=1
        elif op=='SCALE':scale=event['factor']*(1<<event['shift']);counts['scales']+=1
        elif op=='EXECUTE':
            if event['clear']:acc=[0]*event['rows']
            if acc is None or len(acc)!=event['rows']:raise ValueError('missing Add context')
            acc=[x+y*b[0]*scale for x,y in zip(acc,a)]
            if any(not -(1<<63)<=x<1<<63 for x in acc):raise ValueError('Add S64 overflow')
            counts['executes']+=1
        elif op=='READ_FINAL':
            value=final32(acc[event['row']],0);s.write_ack(event['dst'],value&0xffffffff);counts['final_reads']+=1
        elif op=='STORE':
            word=s.read(event['src']);out[event['destination'][1]]=word if word<1<<31 else word-(1<<32)
            counts['external_write_words']+=1
        else:raise ValueError('unknown Add native operation')
    counts['external_words']=counts['external_read_words']+counts['external_write_words']
    return [out[i] for i in range(elements)],dict(counts),s.high
