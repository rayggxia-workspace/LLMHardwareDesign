"""Register measured, finite native tile recipes in the common action pool.

All prior choices are retained. Nothing here selects a model name, instance
count, or a winning schedule. Frontier state still determines resource waits,
static-network legality, and which read-only S contents are invalidated.
"""
from copy import deepcopy
import hashlib
import json
import math

from tile_recipe import cost


def variants_for(ir, qualification, *, service_bindings=None):
    if 'tile_scope' in ir:
        raise ValueError('tile candidates already added')
    if 'primitive_stages' not in ir:
        raise ValueError('tile recipes require explicit primitive/preparation stages')
    if qualification.get('kind')!='native-p-e-tile-services-v1':
        raise ValueError('native tile service qualification required')
    # The same E leaf can have different surrounding service/S adapters.
    # A macro letter alone never licenses reuse of a whole-service latency.
    declared=service_bindings or ir['hardware'].get('tile_service_bindings',{})
    digest=hashlib.sha256(json.dumps(qualification,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    if (declared.get('kind')!='native-tile-instance-services-v1' or
        declared.get('qualification_sha256')!=digest or
        any(not isinstance(declared.get(role),list) or len(set(declared[role]))!=len(declared[role])
            for role in ('P','E')) or not declared.get('evidence')):
        raise ValueError('explicit instance-to-qualified-service bindings required')
    for role,macro in (('P','M'),('E','E')):
        if any(g not in ir['hardware']['leaf_inventory'] or macro not in ir['hardware']['leaf_inventory'][g]['macros']
               for g in declared[role]):
            raise ValueError('declared tile instance capability differs')
    h=ir['hardware'];nodes={n['id']:n for n in ir['primitive_program']['instructions']}
    formats=ir['primitive_program'].get('initial_formats',{})
    program={p['id']:p for p in ir['program']}
    # Nine immutable full-word records: all-zero padding and eight one-hot
    # S16 vectors. They are actual external objects and every use is charged.
    base=ir['required_external_bytes']//16
    constants={'kind':'native-tile-s16-basis-v1','address_words':base,'words':9,
               'records':[[0]*8]+[[int(i==j) for i in range(8)] for j in range(8)]}
    limit=(1<<h['virtual_memory']['address_bits'])//16
    if h.get('external_capacity_words') is not None:
        limit=min(limit,h['external_capacity_words'])
    if base+constants['words']>limit:
        raise ValueError('tile constants exceed external capacity')
    eligible=added=0;reasons={}
    for task in ir['tasks']:
        node=nodes.get(task['id']);prep=ir.get('operand_preparations',{}).get(task['id'])
        if not node or node['op']!='Dot' or not prep:
            continue
        if ir['native_operand_components'][node['id']]!=[3,1]:
            continue
        b_format=formats.get(node['inputs'][1],{})
        bshape=b_format.get('shape',[])
        k=node['attributes']['length'];columns=node['shape'][-1]
        rows=math.prod(node['shape'])//columns
        # An initializer may have a transposed offline view. Its frozen shape
        # and source/literal provenance prove that all grouped rows share B.
        if (b_format.get('bits')!=16 or len(bshape)<2 or bshape[-2:]!=[k,columns] or
            any(d!=1 for d in bshape[:-2]) or
            not (b_format.get('source_file') or 'literal' in b_format)):
            reasons['B_not_proved_static_shared']=reasons.get('B_not_proved_static_shared',0)+1
            continue
        shift=node['attributes'].get('shift')
        if type(shift)!=int or not 0<=shift<=63:
            reasons['native_final_shift']=reasons.get('native_final_shift',0)+1;continue
        bases={b['macro_binding']['M']:b for b in task['bindings']
               if set(b.get('macro_binding',{}))=={'M'} and
               not b.get('read_cache') and not b.get('dot_tile')}
        if not bases:
            continue
        eligible+=1
        limits=sorted({(min(r,rows),min(n,columns)) for r,n in qualification['shapes']})
        for group,original in sorted(bases.items()):
            if group not in declared['P']:continue
            pm=h['leaf_inventory'][group];psite=pm['site']
            if h['resources'][pm['io_resource']]!=1:
                continue
            for rt,ct in limits:
                e_groups=([None] if ct==1 else sorted(g for g,m in h['leaf_inventory'].items()
                    if g in declared['E']
                    and 'E' in m['macros'] and m['site']!=psite and h['resources'][m['io_resource']]==1))
                for eg in e_groups:
                    em=h['leaf_inventory'][eg] if eg is not None else None
                    try:stats=cost(rows,columns,k,rt,ct,qualification,h['virtual_memory'],pm,em)
                    except ValueError:
                        continue  # Exact measured tail/accumulator restrictions.
                    scratch={psite:stats['P_words']}
                    macro={'M':group};resources=set(original['resources']);nets=set(original['nets'])
                    if eg is not None:
                        scratch[em['site']]=stats['E_words'];macro['E']=eg
                        resources.update([eg+'.E',eg+'.LC.service',em['io_resource'],
                            'virtual-memory.channel.'+str(em['memory_group']%h['virtual_memory']['channels'])])
                        if eg+'.E.context' in h['resources']:resources.add(eg+'.E.context')
                        nets.update(eg+'.E.'+d for d in ('read','write'))
                        nets.update(em['site']+'.io.'+d for d in ('load','store'))
                    if (any(n>h['sites'][s]['words'] for s,n in scratch.items()) or
                        any(r not in h['resources'] or h['resources'][r]!=1 for r in resources) or
                        any(n not in h['nets'] for n in nets)):
                        continue
                    temporary=program[node['id']]['temporary_external_region']
                    if stats['temporary_external_words']>temporary['words']:
                        continue
                    spec={'kind':'prepared-s32-static-b-tile-v1','primitive':node['id'],
                          'rows':rows,'columns':columns,'K':k,'tile':[rt,ct],
                          'components':[3,1],'final_shift':shift,'B':node['inputs'][1],
                          'prepared_A_base':prep['external_base'],
                          'temporary_external_region':deepcopy(temporary),'constant_base':base,
                          'invalidate_read_cache':[psite],
                          'layout':{'A':[0,8],'B':[16,24],'packed':[96,112],
                                    'canonical':[512,576],'E':[0,2]}}
                    b={'id':original['id']+';native-tile='+str(rt)+'x'+str(ct)+
                          (';scatter-E='+eg if eg is not None else ''),
                       'site':psite,'macro_binding':macro,'resources':sorted(resources),'nets':sorted(nets),
                       'ticks':stats['ticks'],'external_read_words':stats['external_read_words'],
                       'external_write_words':stats.get('external_write_words',0),
                       'scratch_by_site':scratch,'scratch_words':max(scratch.values()),
                       'dot_tile':spec,'tile_work':stats}
                    task['bindings'].append(b);added+=1
    if added:
        h['tile_service_profiles']=deepcopy(qualification)
        h['tile_service_bindings']=deepcopy(declared)
        ir['tile_constants']=constants;ir['required_external_bytes']=(base+9)*16
    ir['tile_scope']={'eligible_tasks':eligible,'added_bindings':added,'rejections':reasons,
                     'scope':'measured full-K prepared-S32/static-S16 tile grid, real E/M scalar conversion, explicit external copies',
                     'cache':'streaming; invalidate overlapped read-only Dot prefix, no free local copy or warm hit',
                     'excluded':'dynamic B, unmeasured tails, arbitrary dirty residency, overlap, MC/LC binary and physical acceptance'}
    return ir
