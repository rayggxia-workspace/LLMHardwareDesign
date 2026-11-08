"""Independent native tile contract/cost audit.

Does not import the tile candidate builder, cost recipe or search transition.
The hardware's qualified service table is an input, as for other leaf profiles.
No claim of complete controller/DMA/physical execution follows from this audit.
"""
from collections import Counter
import hashlib
import json
import math

from memory import descriptor_ticks


def check_constants(ir):
    c=ir.get('tile_constants')
    if c is None:
        raise ValueError('missing immutable tile constants')
    records=[[0]*8]+[[int(i==j) for i in range(8)] for j in range(8)]
    if (set(c)!={'kind','address_words','words','records'} or
        c['kind']!='native-tile-s16-basis-v1' or c['records']!=records or
        c['words']!=9 or type(c['address_words'])!=int or c['address_words']<0):
        raise ValueError('tile constants identity/extent differs')
    return {'address_words':c['address_words'],'words':9}


def verify(ir, task, binding):
    h=ir['hardware'];q=h.get('tile_service_profiles',{})
    if q.get('kind')!='native-p-e-tile-services-v1':
        raise ValueError('missing native tile service qualification')
    assignments=h.get('tile_service_bindings',{})
    digest=hashlib.sha256(json.dumps(q,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    if (assignments.get('kind')!='native-tile-instance-services-v1' or
        assignments.get('qualification_sha256')!=digest or not assignments.get('evidence')):
        raise ValueError('unqualified tile instance/service assignment')
    constants=check_constants(ir)
    nodes=[n for n in ir['primitive_program']['instructions'] if n['id']==task['id']]
    if len(nodes)!=1 or nodes[0]['op']!='Dot' or 'primitive_stages' not in ir:
        raise ValueError('tile must cover one explicit Dot stage')
    node=nodes[0];s=binding['dot_tile'];attrs=node['attributes']
    prep=ir.get('operand_preparations',{}).get(node['id'],{})
    if not prep or ir['native_operand_components'][node['id']]!=[3,1]:
        raise ValueError('tile requires prepared S32 A and S16 B')
    k=attrs['length'];cols=node['shape'][-1];rows=math.prod(node['shape'])//cols
    b_format=ir['primitive_program'].get('initial_formats',{}).get(node['inputs'][1],{})
    shape=b_format.get('shape',[])
    if (b_format.get('bits')!=16 or len(shape)<2 or shape[-2:]!=[k,cols] or
        any(x!=1 for x in shape[:-2]) or not (b_format.get('source_file') or 'literal' in b_format)):
        raise ValueError('tile B is not proved static and shared across rows')
    if (type(k)!=int or not 0<k<=(2**63-1)//((2**31+131072)*2**15) or
        type(attrs.get('shift'))!=int or not 0<=attrs['shift']<=63):
        raise ValueError('tile accumulator/final shift outside native bound')
    tile=s.get('tile',[])
    if len(tile)!=2 or any(type(v)!=int or not 1<=v<=8 for v in tile):
        raise ValueError('invalid native tile shape')
    rt,ct=tile
    if rt>rows or ct>cols:
        raise ValueError('tile exceeds whole tensor extent')
    macro=binding['macro_binding'];uses_e=ct>1
    if set(macro)!=({'M','E'} if uses_e else {'M'}):
        raise ValueError('tile has missing/extra M or scatter E')
    if (macro['M'] not in assignments.get('P',[]) or
        (uses_e and macro['E'] not in assignments.get('E',[]))):
        raise ValueError('instance not qualified for tile service boundary')
    p=h['leaf_inventory'][macro['M']];e=h['leaf_inventory'][macro['E']] if uses_e else None
    if ('M' not in p['macros'] or (uses_e and ('E' not in e['macros'] or p['site']==e['site'])) or
        binding['site']!=p['site']):
        raise ValueError('tile macro/site capability differs')
    program=[x for x in ir['program'] if x['id']==node['id']]
    if len(program)!=1:
        raise ValueError('tile primitive stage program is ambiguous')
    temporary=program[0]['temporary_external_region']
    expected_spec={'kind':'prepared-s32-static-b-tile-v1','primitive':node['id'],
        'rows':rows,'columns':cols,'K':k,'tile':tile,'components':[3,1],
        'final_shift':attrs['shift'],'B':node['inputs'][1],
        'prepared_A_base':prep['external_base'],'temporary_external_region':temporary,
        'constant_base':constants['address_words'],'invalidate_read_cache':[p['site']],
        'layout':{'A':[0,8],'B':[16,24],'packed':[96,112],'canonical':[512,576],'E':[0,2]}}
    if s!=expected_spec or any(x in binding for x in ('read_cache','parallel_shards','phase_execution')):
        raise ValueError('tile semantics/layout/cache effects differ')
    # Count a finite rectangular grid independently. Quotients only aggregate
    # identical native commands; they do not infer any additional parallelism.
    shapes=set()
    for shape in q.get('shapes',[]):
        if len(shape)!=2 or any(type(v)!=int or not 1<=v<=8 for v in shape):
            raise ValueError('invalid qualified native shape')
        shapes.add(tuple(shape))
    def split(total,step):
        full,tail=divmod(total,step)
        return [(size,count) for size,count in ((step,full),(tail,int(bool(tail)))) if count]
    def slot(table,key):
        value=table[key]
        if type(value)!=int or value<1:
            raise ValueError('invalid qualified tile service duration')
        return value
    def ptime(r,op):return slot(q['P'][str(r)],op)
    def feed(r,op):return slot(q['feeder'][str(r)],op)
    m=h['virtual_memory']
    load=descriptor_ticks(m,1,'load',p['io_write_ticks'])
    store=descriptor_ticks(m,1,'store',p['io_read_ticks'])
    eload=descriptor_ticks(m,1,'load',e['io_write_ticks']) if uses_e else 0
    estore=descriptor_ticks(m,1,'store',e['io_read_ticks']) if uses_e else 0
    stats=Counter(initial_zero_loads=16,external_read_words=16,ticks=16*load)
    extent=0
    for r,nr in split(rows,rt):
        for n,nn in split(cols,ct):
            if (r,n) not in shapes:raise ValueError('unqualified native tile/tail')
            count=nr*nn;extent=max(extent,512+8*(r-1)+n)
            stats.update({key:count*value for key,value in {
                'dot_A_loads':3*r*k,'dot_B_loads':n*k,'dot_executes':3*k,
                'dot_scales':3*k,'dot_feeds':3*k,'grid_tiles':1,
                'external_read_words':(3*r+n)*k,
                'ticks':(3*r+n)*k*load+3*k*(ptime(r,'scale')+ptime(r,'execute'))+
                        k*(feed(r,'cold')+2*feed(r,'reuse_b'))}.items()})
            if n==1:
                stats.update({key:count*value for key,value in {
                    'external_write_words':r,'canonical_outputs':r,'final_reads':r,
                    'ticks':r*(ptime(r,'final_store')+store)}.items()})
            else:
                packed=r*math.ceil(n/4);outputs=r*n
                stats.update({key:count*value for key,value in {
                    'packed_outputs':packed,'flag_outputs':packed,'e_sign_services':packed,
                    'canonical_outputs':outputs,'final_reads':packed+outputs,
                    'scatter_input_loads':3*outputs,'scatter_basis_loads':3*outputs,
                    'scatter_executes':3*outputs,'scatter_scales':3*outputs,'scatter_feeds':3*outputs,
                    'external_read_words':packed+6*outputs,
                    'external_write_words':2*packed+outputs,
                    'ticks':packed*(ptime(r,'final_store')+store+eload+slot(q,'e_shift_store')+estore)+
                        outputs*(6*load+3*(feed(1,'cold')+ptime(1,'scale')+ptime(1,'execute'))+
                                 ptime(1,'final_store')+store)}.items()})
    expected=dict(stats)
    expected.update(P_words=extent,E_words=2 if uses_e else 0,
        external_words=stats['external_read_words']+stats['external_write_words'],
        temporary_external_words=2*min(rows,rt)*math.ceil(min(cols,ct)/4) if uses_e else 0,
        context='full K until all native final writes/ACKs; scatter reuses M only afterwards',
        reservation='all declared M/E/S/LC/channel resources through final external STORE ACK',
        cost_model='native-p-e-tile-stream-v1')
    if binding.get('tile_work')!=expected:
        raise ValueError('tile native command/descriptor work differs')
    scratch={p['site']:extent}
    if uses_e:scratch[e['site']]=2
    if (binding.get('scratch_by_site')!=scratch or binding['scratch_words']!=max(scratch.values()) or
        any(v>h['sites'][site]['words'] for site,v in scratch.items()) or
        temporary['words']<expected['temporary_external_words']):
        raise ValueError('tile finite S/external temporary allocation differs')
    for field in ('ticks','external_read_words','external_write_words'):
        if binding[field]!=expected[field]:raise ValueError('tile cost differs '+field)
    resources=set();nets=set()
    for kind,group in macro.items():
        meta=h['leaf_inventory'][group]
        resources.update([group+'.'+kind,group+'.LC.service',meta['io_resource'],
            'virtual-memory.channel.'+str(meta['memory_group']%m['channels'])])
        if group+'.'+kind+'.context' in h['resources']:resources.add(group+'.'+kind+'.context')
        nets.update(group+'.'+kind+'.'+direction for direction in ('read','write'))
        nets.update(meta['site']+'.io.'+direction for direction in ('load','store'))
    if (resources!=set(binding['resources']) or nets!=set(binding['nets']) or
        any(h['resources'].get(r)!=1 for r in resources) or any(n not in h['nets'] for n in nets)):
        raise ValueError('tile resource/endpoint coverage differs')
    return 1
