"""Frozen Issue51 service model adaptation: explicit disjoint S input allocation.
No calibrated arithmetic/PPA claim; only paired RQ placement within each shape.
"""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"rq_ports"))
from model import Graph,audit_schedule

def build(rows,k,scale_mode,placement,lanes,window,consumer_cost,jobs=4):
    if rows not in (1,8,16) or k not in (2048,8192) or lanes not in (1,8) or window not in (1,2):raise ValueError('unsupported fixture')
    if placement not in ('near','shared') or scale_mode not in ('static','dynamic_row'):raise ValueError('profile')
    w_banks=(16*k+32767)//32768; a_banks=(rows*k+32767)//32768
    if w_banks+a_banks>6:raise ValueError('prepacked W/A exceed six input S banks')
    g=Graph();elements=rows*16;params=80 if scale_mode=='static' else 5*elements
    last_m=[None]*2;last_v=[None]*2;last_a=[None]*2;last_w=[None]*2;last_rq=None
    last_prefetch=[None]*2;group_index=0;weights={};resident=(16*k<=16384)
    if resident:
        for kb in range(k//128):
            off=kb*2048
            weights[kb]=g.transfer('S0','M0',2048,'S0',f'MW{kb%2}',(),
                source_offset=off,destination_offset=(kb//2)*2048,kind='W8')
    static_meta=None
    if scale_mode=='static':
        dest='MC' if placement=='near' else 'VC';ep='M1' if placement=='near' else 'V1'
        static_meta=g.transfer('S6',ep,80,'S6',dest,(),destination_offset=2048,kind='META')
    for job in range(jobs):
        slot=job%window
        reserve_m=g.add('reserve M slot',1,('control',),(last_m[slot],))
        reserve_v=None
        if placement=='shared':reserve_v=g.add('reserve V slot',1,('control',),(last_v[slot],reserve_m))
        if scale_mode=='dynamic_row':
            dest='MC' if placement=='near' else 'VC';ep='M1' if placement=='near' else 'V1'
            dependency=reserve_m if placement=='near' else reserve_v
            meta=g.transfer('S6',ep,params,'S6',dest,(dependency,),job*params,2048+slot*1280,'META')
        else:meta=static_meta
        previous=reserve_m
        for kb in range(k//128):
            buffer=(job*(k//128)+kb)%2
            ao=kb*rows*128;so=w_banks+ao//32768
            a=g.transfer(f'S{so}','M0',rows*128,f'S{so}',f'MA{buffer}',
                (reserve_m,last_a[buffer]),source_offset=ao%32768,kind='A8')
            if resident:w=weights[kb];wb=kb%2
            else:
                wo=kb*2048;sw=wo//32768;wb=buffer
                w=g.transfer(f'S{sw}','M0',2048,f'S{sw}',f'MW{wb}',
                    (reserve_m,last_w[wb]),source_offset=wo%32768,kind='W8')
            compute=g.add('matrix K128',128+rows+16-2,('matrix',f'MA{buffer}',f'MW{wb}'),
                          (previous,*a,*w),job=job,k_begin=kb*128,k_count=128)
            previous=compute;last_a[buffer]=compute
            if not resident:last_w[wb]=compute
        acc=g.memory('MC',elements*4,slot*1024,(previous,),True,'complete-K INT32')
        if placement=='shared':
            arrived=g.transfer('M0','V0',elements*4,'MC','VC',(acc,reserve_v),slot*1024,slot*1024,'ACC32')
            last_m[slot]=arrived[-1];local='VC'
        else:arrived=[acc];local='MC'
        output=[]
        for begin in range(0,elements,lanes):
            count=min(lanes,elements-begin);pslot=group_index%2
            read=g.memory(local,4*count,slot*1024+4*begin,(*arrived,last_prefetch[pslot]),label='RQ acc read')
            po=2048+(slot*1280 if scale_mode=='dynamic_row' else 0)+5*(begin if scale_mode=='dynamic_row' else begin%16)
            parameter=g.memory(local,5*count,po,(read,*meta),label='RQ M/r read')
            execute=g.add('RQ32 batch',26,('rq',),(parameter,last_rq),job=job,begin=begin,count=count)
            cooldown=g.add('RQ interface gap',2,('rq',),(execute,))
            store=g.memory(local,count,4608+slot*256+begin,(execute,),True,'RQ8 write')
            last_prefetch[pslot]=execute;group_index+=1
            last_rq=g.add('RQ next-start barrier',0,(),(cooldown,store))
            output.append(store)
        if placement=='near':
            reserve_v=g.add('reserve V slot',1,('control',),(last_v[slot],*output))
            output=g.transfer('M0','V0',elements,'MC','VC',(*output,reserve_v),4608+slot*256,4608+slot*256,'ACT8')
            last_m[slot]=output[-1]
        read=g.memory('VC',elements,4608+slot*256,(*output,),label='consumer read')
        consume=g.add('integer row-sum consumer',rows*(2*consumer_cost+1),('vector',),(read,),job=job)
        stored=g.memory('VC',rows*4,5120+slot*64,(consume,),True,'consumer result')
        exported=g.transfer('V0','S7',rows*4,'VC','S7',(stored,),5120+slot*64,job*rows*4,'SUM32')
        last_v[slot]=exported[-1]
        g.leases.extend([dict(kind='M',slot=slot,start=reserve_m,end=last_m[slot]),
                         dict(kind='V',slot=slot,start=reserve_v,end=last_v[slot])])
    return g
