"""Uncalibrated ranking work from descriptor work and the supplied base profile.

Work units are NOT predicted runtime cycles. Resource waits in Algo1 use this
proxy; executable ordering uses completion dependencies, never elapsed time.
TLM must separately measure shared-memory contention and actual retirement.
"""
import json,struct,math
from pathlib import Path
from functools import lru_cache

@lru_cache(None)
def fields():
    from ffn_scope_emit import SCHEMA
    path=SCHEMA
    return {f['name']:(f['offset'],f['bytes']) for f in json.loads(path.read_text())['fields']}

def measure(candidate,hardware):
    profile=hardware['native_leaf_profiles']['measurements'];vm=hardware['virtual_memory']
    memory_word=vm['word_bytes'];period=vm['period'];core=vm['core_period']
    ends=[];read_total=write_total=0;components={}
    for call in candidate['calls']:
        raw=bytes.fromhex(call['descriptor_hex']);schema,_,op,abi,_=struct.unpack_from('<IHHII',raw)
        site=call['group']+'.S';io=hardware['sites'][site]
        reads=128;writes=0;sread=swrite=arithmetic=0 # native descriptor fetch
        if call['direction'] in ('load','store'):
            size=call['byte_count']
            if call['direction']=='load':reads+=size;swrite+=size//16
            else:writes+=size;sread+=size//16
        elif schema==0x31485447:
            reads+=8192+128;swrite+=512
        elif schema==3 and abi==7:
            if op==2:
                n=struct.unpack_from('<H',raw,22)[0];sread=2*n;swrite=n;arithmetic=4*n
            elif op==3:sread=2048;swrite=512;arithmetic=2048
            else:raise ValueError('unknown arithmetic work')
        elif schema==0x31455052:
            sread=96;swrite=32;arithmetic=128*3
        elif schema==0x314d5347:
            n=struct.unpack_from('<H',raw,22)[0];sread=2*n;swrite=n
            arithmetic=2*n*profile['G:{"function":0,"gated":1}']
        elif schema==0x31545441:
            context=struct.unpack_from('<H',raw,16)[0]
            reads+=context*1024;sread=context*96;swrite=context*64+32
            arithmetic=context*8*profile['M:{"columns":8,"k":32}']+context*128
        elif schema==0x44454650:
            n=struct.unpack_from('<H',raw,22)[0];sread=48*n;swrite=16*n;arithmetic=128*n
        elif schema==0x02505001 and op==2:
            f=fields()
            def get(n):
                offset,size=f[n];return int.from_bytes(raw[offset:offset+size],'little')
            records=get('groups')*get('ways')*(get('full_k')//128)
            reads+=records*(1152 if get('flags')&1 else 1088)
            sread=records*16;swrite=get('groups')*get('ways')*2
            arithmetic=records*4*profile['M:{"columns":8,"k":32}']
        else:raise ValueError('missing descriptor work model '+hex(schema))
        memory=math.ceil((reads+writes)/memory_word*period/core)
        work=max(1,memory+sread*io['io_read_ticks']+swrite*io['io_write_ticks']+arithmetic)
        index=call['index']
        if index!=len(ends) or any(d>=index for d in call['after']):raise ValueError('candidate call DAG')
        ends.append(work+max((ends[d] for d in call['after']),default=0))
        read_total+=reads;write_total+=writes
        components[hex(schema)]=components.get(hex(schema),0)+work
    return {'work_units':max(ends,default=1),'read_bytes':read_total,'write_bytes':write_total,
            'schema_work':components,'timing_calibrated':False,
            'scope':'serialized leaf/IO work proxy on call DAG; not performance prediction or numerical acceptance'}
