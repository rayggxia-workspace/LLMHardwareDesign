"""Combine existing native tile grids on independent full-K column ranges.

Each child keeps its own M/S/LC/context and independent E/memory resources.
Only immutable prepared A and B are shared, through real duplicate LOADs.
Temporary regions are disjoint slices of the already-owned stage scratch.
This is a bounded common candidate pool, not an optimal partition oracle.
"""
from copy import deepcopy
from itertools import combinations,product

from tile_recipe import cost


def variants_for(ir, *, max_shards=3,max_bindings=64):
    if 'tile_partition_scope' in ir:raise ValueError('tile partitions already registered')
    if max_shards<2 or max_bindings<1:raise ValueError('invalid tile partition search bounds')
    h=ir['hardware'];q=h['tile_service_profiles'];program={n['id']:n for n in ir['program']}
    total=eligible=truncated=0
    for task in ir['tasks']:
        bases=[b for b in task['bindings'] if 'dot_tile' in b and 'materialized_tile' not in b]
        if not bases:continue
        columns=bases[0]['dot_tile']['columns'];groups=sorted({b['macro_binding']['M'] for b in bases})
        original=program[task['id']]['temporary_external_region'];generated=[];seen=set()
        if len(groups)<2 or columns<2:continue
        eligible+=1
        for count in range(2,min(max_shards,len(groups),columns)+1):
            for selected in combinations(groups,count):
                # Balanced columns and grid-aligned balanced columns; both
                # are bounded alternatives, never an assumed cost/instance.
                quantum=max(b['dot_tile']['tile'][1] for b in bases)
                widths={tuple(columns//count+int(i<columns%count) for i in range(count))}
                chunks,tail=divmod(columns,quantum)
                aligned=[(chunks//count+int(i<chunks%count))*quantum for i in range(count)]
                aligned[-1]+=tail;widths.add(tuple(aligned))
                for widths_for in sorted(widths):
                    if min(widths_for)<1:continue
                    choices=[];lo=0;space=original['words']//count
                    for index,(group,width) in enumerate(zip(selected,widths_for)):
                        best={}
                        for old in bases:
                            if old['macro_binding']['M']!=group:continue
                            rt,ct=old['dot_tile']['tile']
                            if ct>width:continue
                            p=h['leaf_inventory'][group]
                            e=h['leaf_inventory'][old['macro_binding']['E']] if 'E' in old['macro_binding'] else None
                            try:w=cost(old['dot_tile']['rows'],width,old['dot_tile']['K'],rt,ct,q,h['virtual_memory'],p,e)
                            except ValueError:continue
                            if w['temporary_external_words']>space:continue
                            b=deepcopy(old);b['id']+=';column-slice='+str(lo)+':'+str(lo+width)
                            b['dot_tile']['columns']=width;b['tile_work']=w
                            b['dot_tile']['temporary_external_region']={**original,
                                'address_words':original['address_words']+index*space,'words':space}
                            b['tile_column_view']={'columns':[lo,lo+width],'source_columns':columns,
                                                   'external_row_stride_words':columns}
                            for field in ('ticks','external_read_words','external_write_words'):b[field]=w.get(field,0)
                            # Layout addresses stay unchanged; only the measured
                            # tail changes their actually touched extent.
                            scratch={p['site']:w['P_words']}
                            if e:scratch[e['site']]=w['E_words']
                            b['scratch_by_site']=scratch;b['scratch_words']=max(scratch.values())
                            key=(tuple(b['resources']),tuple(b['nets']))
                            if key not in best or (b['ticks'],b['external_read_words'],b['id'])<(
                                best[key]['ticks'],best[key]['external_read_words'],best[key]['id']):best[key]=b
                        choices.append([{'columns':[lo,lo+width],'binding':b} for b in best.values()]);lo+=width
                    for children in product(*choices):
                        leaves=[c['binding'] for c in children];resources=[set(b['resources']) for b in leaves]
                        if any(resources[i]&resources[j] for i in range(count) for j in range(i)):continue
                        key=tuple(b['id'] for b in leaves)
                        if key in seen:continue
                        seen.add(key)
                        if len(generated)>=max_bindings:truncated+=1;continue
                        scratch={s:n for b in leaves for s,n in b['scratch_by_site'].items()}
                        generated.append({'id':'tile-columns['+'|'.join(key)+']','site':leaves[0]['site'],
                            'macro_binding':{},'resources':sorted(set.union(*resources)),
                            'nets':sorted(set().union(*(set(b['nets']) for b in leaves))),
                            'ticks':max(b['ticks'] for b in leaves),'warm_ticks':max(b['ticks'] for b in leaves),
                            'external_read_words':sum(b['external_read_words'] for b in leaves),
                            'external_write_words':sum(b['external_write_words'] for b in leaves),
                            'scratch_by_site':scratch,'scratch_words':max(scratch.values()),
                            'parallel_shards':{'kind':'dot-columns-v1','primitive':task['id'],
                                               'columns':columns,'children':deepcopy(list(children))},
                            'tile_partition':{'kind':'native-tile-columns-v1',
                                'temporary':'disjoint-slices-of-original-stage-region'}})
        task['bindings'].extend(generated);total+=len(generated)
    ir['tile_partition_scope']={'eligible_tasks':eligible,'added_bindings':total,'truncated_bindings':truncated,
        'max_shards':max_shards,'max_bindings_per_task':max_bindings,
        'scope':'independent native full-K output-column tile grids, real duplicate input LOADs and disjoint external scratch',
        'excluded':'K sharding, shared-resource overlap, materialized child windows, general dirty residency or system qualification'}
    return ir
