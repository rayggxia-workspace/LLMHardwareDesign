"""Optional full-K output-column partitions on independent M instances.

This is a common action pool for greedy and DP. Each child retains the existing
serial native recipe, S lease, LC token and memory-channel reservation. Sharing
a channel serializes children; no duration is divided by an instance count.
The initial family covers prepared A / S16 B only: compute uses no shared
temporary writes and output columns have disjoint external destinations.
"""
from copy import deepcopy
from itertools import combinations, permutations, product
import math

from dot_cache import variants
from dynamic_columns import warm_bound
from dynamic_columns import resized


def _partition(columns, groups, hardware, channel_balanced):
    channels=[hardware['leaf_inventory'][g]['memory_group'] %
              hardware['virtual_memory']['channels'] for g in groups]
    # Integer weights avoid float-dependent partition boundaries. Give each
    # channel equal aggregate width even when several M share that channel.
    counts=[channels.count(c) for c in channels]
    scale=math.lcm(*counts)
    weights=[scale//c if channel_balanced else 1 for c in counts]
    total=sum(weights);widths=[columns*w//total for w in weights]
    order=sorted(range(len(groups)),key=lambda i:(-(columns*weights[i]%total),groups[i]))
    for i in order[:columns-sum(widths)]:widths[i]+=1
    return widths


def variants_for(ir, *, max_shards=4, max_bindings=512, dynamic=True):
    """Bounded partitions, not an exhaustive tiling or optimality claim.

    Existing single-instance/cache choices remain untouched. Compound choices
    use streaming or the largest legal prefix independently on each M; all
    retention policies are evaluated against the current frontier at runtime.
    """
    if 'column_shard_scope' in ir:raise ValueError('column shards already added')
    if 'primitive_stages' not in ir:raise ValueError('column shards require primitive stages')
    if max_shards<2 or max_bindings<1:raise ValueError('positive column search bounds required')
    nodes={n['id']:n for n in ir['primitive_program']['instructions']}
    eligible=added=truncated=dynamic_count=0;h=ir['hardware']
    for task in ir['tasks']:
        node=nodes.get(task['id'])
        if (not node or node['op']!='Dot' or node['id'] not in ir.get('operand_preparations',{}) or
            ir['native_operand_components'][node['id']][1]!=1):continue
        columns=node['shape'][-1]
        bases={b['macro_binding']['M']:b for b in task['bindings']
               if not b.get('read_cache') and set(b.get('macro_binding',{}))=={'M'}}
        if len(bases)<2 or columns<2:continue
        eligible+=1;generated=[];seen=set()
        for count in range(2,min(len(bases),columns,max_shards)+1):
            for groups in combinations(sorted(bases),count):
                if len({bases[g]['site'] for g in groups})!=count:continue
                widths_options={tuple(_partition(columns,groups,h,b)) for b in (False,True)}
                for widths in sorted(widths_options):
                    if min(widths)<1:continue
                    choices=[];lo=0
                    for group,width in zip(groups,widths):
                        child=deepcopy(bases[group])
                        for field in ('ticks','external_read_words','external_write_words'):
                            if child[field]%columns:raise ValueError('nonuniform Dot column work')
                            child[field]=child[field]//columns*width
                        child['id']+=';columns='+str(lo)+':'+str(lo+width)
                        shard_node=deepcopy(node);shard_node['shape'][-1]=width
                        proxy={'hardware':h,'tasks':[{'id':task['id'],'bindings':[child]}],
                               'primitive_stages':ir['primitive_stages'],
                               'primitive_program':{'instructions':[shard_node]},
                               'native_operand_components':ir['native_operand_components']}
                        variants(proxy,state_cost=True)
                        cached=[b for b in proxy['tasks'][0]['bindings'] if b.get('read_cache')]
                        if not cached:choices.append([{'columns':[lo,lo+width],'binding':child}])
                        else:
                            ends={min(b['read_cache']['stripe'] for b in cached),
                                  max(b['read_cache']['stripe'] for b in cached)}
                            choices.append([{'columns':[lo,lo+width],'binding':b} for b in cached
                                            if b['read_cache']['stripe'] in ends])
                        lo+=width
                    for selected in product(*choices):
                        for ordered in permutations(selected):
                            key=tuple(c['binding']['id'] for c in ordered)
                            if key in seen:continue
                            seen.add(key)
                            if len(generated)>=max_bindings:
                                truncated+=1;break
                            children=deepcopy(list(ordered));leaves=[c['binding'] for c in children]
                            scratch={s:n for b in leaves for s,n in b['scratch_by_site'].items()}
                            generated.append({'id':'column-shards['+'|'.join(key)+']',
                                'site':leaves[0]['site'],'macro_binding':{},
                                'resources':sorted(set().union(*(set(b['resources']) for b in leaves))),
                                'nets':sorted(set().union(*(set(b['nets']) for b in leaves))),
                                'ticks':max(b['ticks'] for b in leaves),
                                'warm_ticks':max(b.get('warm_ticks',b['ticks']) for b in leaves),
                                'external_read_words':sum(b['external_read_words'] for b in leaves),
                                'external_write_words':sum(b['external_write_words'] for b in leaves),
                                'scratch_by_site':scratch,'scratch_words':max(scratch.values()),
                                'parallel_shards':{'kind':'dot-columns-v1','primitive':node['id'],
                                    'columns':columns,'children':children}})
                        if len(generated)>=max_bindings:break
                    if len(generated)>=max_bindings:break
                if len(generated)>=max_bindings:break
            if len(generated)>=max_bindings:break
        if dynamic:
            families=set();adaptive=[]
            for b in generated:
                children=b['parallel_shards']['children'];leaves=[c['binding'] for c in children]
                resources=[set(c['resources']) for c in leaves]
                if any(resources[i]&resources[j] for i in range(len(resources)) for j in range(i)):
                    continue
                key=tuple((c['macro_binding']['M'],c.get('read_cache',{}).get('stripe')) for c in leaves)
                if key in families:continue
                families.add(key);candidate=deepcopy(b)
                candidate['id']+=';frontier-waterfill'
                candidate['frontier_partition']={'kind':'disjoint-affine-waterfill-v1'}
                candidate['warm_ticks']=warm_bound(children,columns)
                adaptive.append(candidate)
            generated.extend(adaptive);dynamic_count+=len(adaptive)
        task['bindings'].extend(generated);added+=len(generated)
    ir['column_shard_scope']={'eligible_tasks':eligible,'added_bindings':added,
        'max_shards':max_shards,'max_static_bindings_per_task':max_bindings,'truncated_families':truncated,
        'frontier_partition_bindings':dynamic_count,
        'partitions':'balanced, channel balanced, and frontier-affine waterfill on disjoint resources; all child issue orders',
        'cache_choices':'stream or largest legal read-only prefix per child; dynamic preserve/shrink/discard',
        'scope':'full-K disjoint output columns; prepared A shared; S16 B; native arithmetic unchanged',
        'excluded':'K partitions, dirty output residency, intra-service overlap, arbitrary partitions, LC encoding'}
    return ir


def leaves(binding):
    return [c['binding'] for c in binding['parallel_shards']['children']] if 'parallel_shards' in binding else [binding]


def leaf_rows(row):
    return row['evaluation']['services'] if row.get('evaluation',{}).get('cost_model') in (
        'dot-column-shards-v1','dot-phased-column-shards-v1') else [row]


def expand_selected(tasks,plan):
    """Flatten selected compound schedules for diagnostics/numeric event counts.

    This helper is NOT used by the independent schedule or native checker.
    """
    by_id={t['id']:t for t in tasks};expanded=[];rows=[];owners={}
    for row in plan['tasks']:
        task=by_id[row['id']];b=next(b for b in task['bindings'] if b['id']==row['binding'])
        deps=[x for p in task.get('after',[]) for x in owners[p]]
        if 'parallel_shards' in b:
            services=leaf_rows(row);owners[task['id']]=[s['id'] for s in services]
            children=b['parallel_shards']['children']
            if 'frontier_partition' in b:
                children=[resized(c,*r) for c,r in zip(children,row['evaluation']['resolved_columns'])]
            for child,s in zip(children,services):
                expanded.append({'id':s['id'],'after':deps,'bindings':[child['binding']],
                                 'source_task':task['id'],'columns':child['columns']})
                rows.append(s)
        else:
            owners[task['id']]=[task['id']]
            expanded.append({**task,'after':deps,'bindings':[b],'source_task':task['id']});rows.append(row)
    return expanded,{**plan,'tasks':rows}
