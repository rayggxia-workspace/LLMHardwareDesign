"""Register serialized resident loops as optional convex graph-cover actions.

Original tasks/bindings remain intact. Whole-record commands and all required
external transfers survive. Each element starts cold and commits live-outs;
there is deliberately no free cross-element or cross-service residency.
"""
from copy import deepcopy
import hashlib
import json
import math

from native_pointwise import bind_external,lower,regions
from resident_records import plan
from resident_survey import build_actors
from resident_timing import audit


STRATEGIES=(('spill',1,True,'copy_cost'),('greedy',1,False,'copy_cost'),
            ('dp',None,False,'copy_cost'),('future_greedy',1,False,'future_copies'),
            ('future_dp',None,False,'future_copies'))


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def uniform_contract(ir,names):
    """Algebraic whole-loop restriction, not extrapolation from three samples.

External arrays must be directly allocated and either scalar or exactly the
output shape. Hence each record identity is (tensor,i) or (tensor,0), never an
index-dependent alias through broadcasting/views. Every iteration has the
same native command/identity topology and its live-outs are committed first.
"""
    p=ir['primitive_program'];nodes={n['id']:n for n in p['instructions']}
    formats={**p.get('initial_formats',{}),**nodes};shape=nodes[names[0]]['shape']
    members=set(names);sources=set().union(*(set(nodes[n]['inputs']) for n in names))-members
    modes={};intervals=[];alloc={**ir['external_regions'],**ir['primitive_regions']}
    for name in sorted(sources):
        f=formats[name];s=f['shape']
        if math.prod(s)==1:mode='scalar';extent=1
        elif s==shape:mode='element';extent=math.prod(shape)
        else:raise ValueError('resident loop needs scalar or same-shape external sources')
        if extent>1 and (f.get('op')=='Constant' or 'literal' in f):
            raise ValueError('resident loop needs an indexed literal source contract')
        if f.get('op')=='View' or name not in alloc:
            raise ValueError('resident loop source needs a direct reserved allocation')
        r=alloc[name]
        if r['words']<extent:raise ValueError('resident source allocation shorter than shape')
        modes[name]=mode;intervals.append((r['address_words'],r['address_words']+extent,name))
    for lo,hi,name in intervals:
        if any(n!=name and max(lo,a)<min(hi,b) for a,b,n in intervals):
            raise ValueError('resident loop sources have aliased allocation ranges')
    return {'kind':'direct-scalar-or-element-loop-v1','elements':math.prod(shape),'shape':shape,
            'sources':modes,'iteration_order':'ascending, serial; cold records/banks; all live-outs STORE-ACKed'}


def requirements(h,actors):
    resources=set();nets=set();scratch={}
    for group,a in actors.items():
        m=h['leaf_inventory'][group];kind=a['kind'];site=a['site']
        resources.update((group+'.'+kind,group+'.LC.service',m['io_resource'],
                          'virtual-memory.channel.'+str(m['memory_group']%h['virtual_memory']['channels'])))
        if kind=='M':resources.add(group+'.M.context')
        nets.update((group+'.'+kind+'.read',group+'.'+kind+'.write',site+'.io.load',site+'.io.store'))
        # Reserve the allocator's entire finite store. This is conservative;
        # no retained prefix is allowed to overlap the resident program.
        scratch[site]=a['words']
    return sorted(resources),sorted(nets),scratch


def region_choices(program,lengths=()):
    """Keep maximal runs and optionally expose overlapping smaller covers.

    These are search-space bounds, not model-specific fusion decisions.
    Selecting the partition/binding remains a frontier action.
    """
    if any(type(n)!=int or n<1 for n in lengths):raise ValueError('positive resident cover lengths required')
    seen=set();result=[]
    for run in regions(program):
        groups=[run]+[run[i:i+n] for n in sorted(set(lengths)) if n<len(run) for i in range(len(run)-n+1)]
        for group in groups:
            key=tuple(group)
            if key not in seen:seen.add(key);result.append(group)
    return result


def variants_for(ir,timing,*,width=8,names_list=None,cover_lengths=(),continuation=False,value_reuse=False):
    if 'resident_actions' in ir:raise ValueError('resident covers already registered')
    canonical=build_actors(ir,timing);h=ir['hardware'];declared=h['tile_service_bindings']
    actions=[];recipes={};rejected=[]
    tasks={t['id']:t for t in ir['tasks']};zero=ir['native_constants']['0']['address_words']
    source=digest(ir['primitive_program'])
    for names in (region_choices(ir['primitive_program'],cover_lengths) if names_list is None else names_list):
        if not set(names)<=tasks.keys():
            rejected.append({'primitives':names,'reason':'region is not a set of original compute tasks'});continue
        try:
            loop=uniform_contract(ir,names);graph=bind_external(lower(ir['primitive_program'],names,0),ir)
            from resident_timing import event_ticks
            for op in graph['operations']:
                if op['kind']=='M':
                    event_ticks({'op':'M_FINAL','width':op['width'],'shift':op['shift']},timing)
                    for reuse in (False,True):event_ticks({'op':'M_TERM','k':op['k'],'reuse_b':reuse},timing)
                else:event_ticks({'op':'E','opcode':op['opcode'],'shift':op['shift'],'inputs':op['inputs']},timing)
            options=[];graphs=[('',graph)]
            if value_reuse:
                from native_reuse import rewrite
                shared=rewrite(graph)
                if any(n.get('reuse_of') for n in shared['operations']):graphs.append(('reuse_',shared))
            for prefix,body_graph in graphs:
                for strategy,w,spill,rank in STRATEGIES:
                    candidate=plan(body_graph,canonical,zero,width=width if w is None else w,
                        spill_all=spill,rank_policy=rank,service_timing=timing)
                    if candidate['status']!='planned':raise ValueError('resident native program has no legal allocation')
                    audit(candidate,timing);options.append((prefix+strategy,candidate,None,body_graph))
                    if continuation:
                        from resident_continuation import compile_loop
                        try:
                            sequence=compile_loop(body_graph,loop,canonical,zero,width=width if w is None else w,
                                spill_all=spill,rank_policy=rank,service_timing=timing)
                        except ValueError as error:
                            rejected.append({'primitives':names,'strategy':prefix+strategy+'_continue','reason':str(error)})
                        else:options.append((prefix+strategy+'_continue',sequence['programs'][0],sequence,body_graph))
        except ValueError as error:
            # Unqualified shapes/commands stay on the unchanged original path.
            rejected.append({'primitives':names,'reason':str(error)});continue
        bindings=[]
        for strategy,candidate,sequence,body_graph in options:
            recipe={'kind':'serial-native-resident-loop-v1','source_program_sha256':source,
                'primitives':names,'loop':loop,'graph':body_graph,'plan':candidate,'strategy':strategy}
            if candidate.get('value_reuse'):recipe['value_reuse']=candidate['value_reuse']
            if sequence is not None:
                recipe['loop']={**loop,'iteration_order':'ascending, serial; verified read-only continuation; all live-outs STORE-ACKed'}
                recipe['continuation_loop']=sequence
            total=sequence['totals'] if sequence is not None else {
                field:loop['elements']*candidate[field] for field in
                ('total_ticks','external_load_words','external_store_words')}
            key=digest(recipe);recipes[key]=recipe
            for pg in declared['P']:
                for eg in declared['E']:
                    actors={}
                    actor_map={old:(pg if a['kind']=='M' else eg) for old,a in canonical.items()}
                    for old,new in actor_map.items():
                        a=canonical[old];m=h['leaf_inventory'][new]
                        # Rebinding requires identical finite storage and IO
                        # contract, not just an equal macro operation letter.
                        if (m['words']!=a['words'] or m['io_read_ticks']!=h['leaf_inventory'][old]['io_read_ticks'] or
                            m['io_write_ticks']!=h['leaf_inventory'][old]['io_write_ticks']):
                            raise ValueError('resident instance contract differs from template allocator')
                        actors[new]={**a,'site':m['site']}
                    resources,nets,scratch=requirements(h,actors);count=loop['elements']
                    bindings.append({'id':'resident:'+strategy+':M='+pg+'/E='+eg,'site':h['leaf_inventory'][pg]['site'],
                        'ticks':total['total_ticks'],'resources':resources,'nets':nets,
                        'scratch_words':actors[pg]['words'],'scratch_by_site':scratch,
                        'external_read_words':total['external_load_words'],
                        'external_write_words':total['external_store_words'],
                        'macro_binding':{'M':pg,'E':eg},'resident_region':{
                            'kind':'serial-native-resident-loop-v1','recipe':key,'elements':count,
                            'actor_map':actor_map,
                            'invalidate_read_cache':sorted(scratch)}})
        actions.append({'id':'@resident:'+names[0]+':'+names[-1],'covers':list(names),'bindings':bindings})
        print(json.dumps({'phase':'resident-region-registered','first':names[0],'last':names[-1],
            'primitives':len(names),'elements':loop['elements'],'bindings':len(bindings)}),flush=True)
    ir['resident_actions']=actions;ir['resident_recipes']=recipes;ir['resident_timing']=deepcopy(timing)
    ir['resident_scope']={'source_program_sha256':source,'rejected':rejected,
        'scope':'optional serialized native resident loop cover actions; explicit virtual-memory and measured P/E slots; no full model execution, controller/DMA/system, energy, token/s or physical qualification'}
    return ir
