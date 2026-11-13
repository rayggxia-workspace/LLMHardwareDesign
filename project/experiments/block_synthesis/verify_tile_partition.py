"""Independent column coverage, address, resource and tile command audit."""
from verify_tile_binding import verify as verify_tile


def verify(ir,task,binding):
    if (binding.get('tile_partition')!={'kind':'native-tile-columns-v1',
            'temporary':'disjoint-slices-of-original-stage-region'} or
        any(k in binding for k in ('dot_tile','frontier_partition','materialized_tile','read_cache'))):
        raise ValueError('unknown tile partition semantics')
    spec=binding['parallel_shards'];nodes=[n for n in ir['primitive_program']['instructions'] if n['id']==task['id']]
    if len(nodes)!=1 or nodes[0]['op']!='Dot':raise ValueError('tile partition requires one Dot')
    columns=nodes[0]['shape'][-1];children=spec['children']
    if spec.get('kind')!='dot-columns-v1' or spec.get('primitive')!=task['id'] or spec.get('columns')!=columns or len(children)<2:
        raise ValueError('tile partition identity/extent differs')
    phased='phase_execution' in binding
    if phased and binding['phase_execution']!={'kind':'native-tile-compound-fcfs-v1',
        'reservation':'all-union-resources-through-final-ACK'}:raise ValueError('unknown tile phase protocol')
    coverage=[];regions=[];seen=set();scratch={};nets=set();leaves=[];checked=0;shared=False;recipes=set()
    for child in children:
        lo,hi=child['columns'];leaf=child['binding']
        if type(lo)!=int or type(hi)!=int or not 0<=lo<hi<=columns:raise ValueError('invalid tile partition range')
        if 'dot_tile' not in leaf or any(k in leaf for k in ('parallel_shards','materialized_tile','tile_partition')):
            raise ValueError('tile partition needs serial native tile children')
        temp=leaf['dot_tile']['temporary_external_region']
        checked+=verify_tile(ir,task,leaf,column_range=(lo,hi),temporary=temp)
        rs=set(leaf['resources'])
        overlap=rs&seen
        if overlap and (not phased or any(not r.startswith('virtual-memory.channel.') for r in overlap)):
            raise ValueError('tile partition children share resources')
        shared|=bool(overlap);s=leaf['dot_tile'];recipes.add((s['rows'],s['K'],tuple(s['tile'])))
        seen|=rs;nets.update(leaf['nets']);scratch.update(leaf['scratch_by_site']);leaves.append(leaf)
        coverage.append((lo,hi));regions.append((temp['address_words'],temp['address_words']+temp['words']))
    at=0
    for lo,hi in sorted(coverage):
        if lo!=at:raise ValueError('tile partition column gap/overlap')
        at=hi
    if at!=columns:raise ValueError('tile partition incomplete columns')
    if phased and (not shared or len(recipes)!=1 or len(children)>min(
        ir['hardware']['virtual_memory'][k] for k in ('queue','slots','credits'))):
        raise ValueError('tile phases need one grid recipe, shared channels and finite requests')
    if any(a[1]>b[0] for a,b in zip(sorted(regions),sorted(regions)[1:])):
        raise ValueError('tile partition temporary regions overlap')
    if (binding.get('macro_binding')!={} or binding['site']!=leaves[0]['site'] or
        binding['scratch_by_site']!=scratch or binding['scratch_words']!=max(scratch.values()) or
        binding['ticks']!=max(b['ticks'] for b in leaves) or binding['warm_ticks']!=binding['ticks'] or
        set(binding['resources'])!=seen or set(binding['nets'])!=nets):
        raise ValueError('tile partition aggregate differs')
    for field in ('external_read_words','external_write_words'):
        if binding[field]!=sum(b[field] for b in leaves):raise ValueError('tile partition traffic differs')
    return checked
