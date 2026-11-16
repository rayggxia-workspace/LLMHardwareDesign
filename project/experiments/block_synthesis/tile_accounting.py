"""Attribute checked tile time to service boundaries and real descriptors.

P service boundaries include local adaptation/ACK. They are deliberately not
labelled pure MAC cycles. Use only after the independent binding audit.
"""
from collections import Counter
from memory import descriptor_ticks


def charge(binding,hardware):
    s=binding['dot_tile'];q=hardware['tile_service_profiles'];result=Counter()
    pm=hardware['leaf_inventory'][binding['macro_binding']['M']]
    em=hardware['leaf_inventory'][binding['macro_binding']['E']] if 'E' in binding['macro_binding'] else None
    memory=hardware['virtual_memory']
    pl=descriptor_ticks(memory,1,'load',pm['io_write_ticks'])
    pw=descriptor_ticks(memory,1,'store',pm['io_read_ticks'])
    el=descriptor_ticks(memory,1,'load',em['io_write_ticks']) if em else 0
    ew=descriptor_ticks(memory,1,'store',em['io_read_ticks']) if em else 0
    result['external_load']=binding['tile_work']['initial_zero_loads']*pl
    rt,ct=s['tile'];rows,columns,k=s['rows'],s['columns'],s['K']
    def groups(total,size):
        n,r=divmod(total,size)
        return [(v,c) for v,c in ((size,n),(r,int(bool(r)))) if c]
    for r,nr in groups(rows,rt):
        p=q['P'][str(r)];f=q['feeder'][str(r)]
        for n,nn in groups(columns,ct):
            count=nr*nn;result['external_load']+=count*k*(3*r+n)*pl
            result['tile_P_service']+=count*3*k*(p['scale']+p['execute'])
            result['tile_feeder']+=count*k*(f['cold']+2*f['reuse_b'])
            if n==1:
                result['tile_P_service']+=count*r*p['final_store']
                result['external_store']+=count*r*pw
            else:
                packed=r*((n+3)//4);out=r*n;p1=q['P']['1']
                result['tile_P_service']+=count*(packed*p['final_store']+
                    out*(3*(p1['scale']+p1['execute'])+p1['final_store']))
                result['tile_E_service']+=count*packed*q['e_shift_store']
                result['tile_feeder']+=count*3*out*q['feeder']['1']['cold']
                result['external_load']+=count*(packed*el+6*out*pl)
                result['external_store']+=count*(packed*(pw+ew)+out*pw)
    if sum(result.values())!=binding['ticks']:raise ValueError('tile time attribution does not conserve')
    return result


def traffic(binding):
    w=binding['tile_work']
    reads={'tile_A_loads':w['dot_A_loads'],'tile_static_B_loads':w['dot_B_loads'],
        'tile_zero_loads':w['initial_zero_loads'],
        'tile_packed_E_loads':w.get('packed_outputs',0),
        'tile_scatter_input_loads':w.get('scatter_input_loads',0),
        'tile_scatter_basis_loads':w.get('scatter_basis_loads',0)}
    writes={'tile_packed_stores':w.get('packed_outputs',0),
        'tile_flag_stores':w.get('flag_outputs',0),'tile_canonical_stores':w['canonical_outputs']}
    if sum(reads.values())!=binding['external_read_words'] or sum(writes.values())!=binding['external_write_words']:
        raise ValueError('tile traffic attribution does not conserve')
    return reads,writes
