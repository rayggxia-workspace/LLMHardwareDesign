"""Whole graph native candidate selection and same-plan descriptor deployment."""
from copy import deepcopy
from hashlib import sha256
from math import prod
import json
from native_backend import NativeBackend
from native_u_candidates import candidate as u_candidate
from native_p_candidates import candidate as p_candidate
from native_projection_candidates import candidate as projection_candidate
from native_gather_candidates import candidate as gather_candidate
from native_concat_candidates import candidate as concat_candidate
from native_ffn_candidates import candidate as ffn_candidate,workspace_requirements
from native_wiring import merge,selected_plan
from native_work_cost import measure
from native_completion import attach as attach_completion
from pack_native_projections import projection_size,ORDINARY
from loop_dp import search
from verify_loop_dp import verify

def digest(value):
    return sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def allocations(graph,recipes,layouts,hardware):
    required=set();indices=set();exponents={}
    for task in recipes['tasks']:
        if task['kind']=='View':continue
        for tile in task['tiles']:
            required.add(tile['write']['value'])
            for a in tile.get('read',[])+tile.get('key_rows',[])+tile.get('value_rows',[]):required.add(a['root'])
            if task['kind']=='Gather':
                required.add(tile['indexed_table']);indices.add(tile['read'][0]['root'])
    for task in graph['tasks']:
        if task['kind']=='RoPE':
            for k in ('cosine','sine'):exponents[layouts['values'][task['details'][k]['tensor']]['root']]=-14
    regions={};base=0x10000000;requirements=[]
    def allocate(name,size,exponent=-16,**extra):
        nonlocal base
        region={'value':name,'base':base,'bytes':size,'element_bytes':4,'exponent':exponent,**extra}
        regions[name]=region;base+=(size+8191)//8192*8192
        return region
    produced={v for t in graph['tasks'] for v in t['outputs']}
    for name in sorted(required):
        value=graph['values'][name];size=4*prod(value['shape'])
        r=allocate(name,size,exponents.get(name,-16),**({'encoding':'signed-int32-exact'} if name in indices else {}))
        if name not in produced:
            requirements.append({'kind':'input_tensor','region':r,'source_dtype':value['dtype'],
                                 'source_shape':value['shape'],'materialized':False})
    workspaces={}
    for task in recipes['tasks']:
        if task['kind']=='SwiGLUFFN':
            for name,spec in workspace_requirements(task).items():allocate(name,4*spec['elements'])
        elif task['kind']=='Attention':
            # A conservative allocation; actual candidates report the used prefix.
            size=max(512,sum(512*(len(t['key_rows'])+len(t['value_rows'])) for t in task['tiles']))
            workspaces[task['id']]=allocate(task['id']+':kv_workspace',size)
    weights={}
    for task in recipes['tasks']:
        for tile in task['tiles']:
            names=[tile['weight']['value']] if task['kind']=='MatMul' else tile['weights'] if task['kind']=='SwiGLUFFN' else []
            for name in names:
                if name in weights:continue
                k,n=graph['values'][name]['shape'];size=projection_size(n,k,base,ORDINARY)
                weights[name]={'shape':[n,k],'format':ORDINARY,'base':base,'bytes':size}
                requirements.append({'kind':'packed_weight','graph_value':name,**weights[name],'materialized':False})
                base+=(size+8191)//8192*8192
    if base>1<<hardware['virtual_memory']['address_bits']:raise ValueError('native allocation exceeds base DDR aperture')
    return {'regions':regions,'weights':weights,'attention_workspaces':workspaces,
            'runtime_asset_requirements':requirements,'end_address':base,
            'scope':'static allocation and asset requirements; data images are not materialized'}

def options(task,hardware):
    targets=hardware['native_dispatch_overlay']['targets']
    us=[t['group'] for t in targets if t['group'].startswith('U')]
    ps=[t['group'] for t in targets if any(r['schema']==0x31535744 for r in t['routes'])]
    if task['kind'] in ('Gather','RMSNorm','Add','Concat'):return [{'group':u} for u in us]
    if task['kind'] in ('RoPE','Attention'):return [{'group':p} for p in ps]
    if task['kind'] in ('MatMul','SwiGLUFFN'):return [{'source':u,'target':p} for u in us for p in ps]
    raise ValueError('missing native candidate family '+task['kind'])

def encode(task,option,storage,hardware,identities):
    common={'regions':storage['regions'],'profile':hardware['native_dispatch_overlay']}
    kind=task['kind']
    if kind in ('RMSNorm','Add'):return u_candidate(task,**option,**common)
    if kind=='Gather':return gather_candidate(task,**option,**common)
    if kind=='Concat':return concat_candidate(task,**option,**common)
    if kind in ('RoPE','Attention'):
        # Workspace belongs to the candidate, not an operand allocation.
        own=storage['attention_workspaces'].get(task['id'])
        common['regions']={k:v for k,v in storage['regions'].items() if own is None or k!=own['value']}
        return p_candidate(task,**option,**common,workspace=own)
    fn=projection_candidate if kind=='MatMul' else ffn_candidate
    return fn(task,**option,regions=storage['regions'],weights=storage['weights'],
              hardware=hardware,identities=identities)

def compile(graph,recipes,layouts,hardware,*,width=8,progress=lambda x:None):
    storage=allocations(graph,recipes,layouts,hardware)
    tasks_by={t['id']:t for t in recipes['tasks']}
    ancestors={}
    for t in recipes['tasks']:
        ancestors[t['id']]=set().union(*(ancestors[p] if tasks_by[p]['kind']=='View' else {p} for p in t['after']))
    hardware=deepcopy(hardware)
    hardware['nets']={};hardware['incompatible_nets']=[]
    dp_tasks=[];choice={};wire_by_net={}
    test_ids={'first_session':1,'generation':1,'job':1,'epoch':1,'tensor':1,'version':1,'rf_object_base':0,'record_sequence_base':0}
    for t in recipes['tasks']:
        if t['kind']=='View':continue
        bindings=[]
        for option in options(t,hardware):
            c=encode(t,option,storage,hardware,test_ids)
            cost=measure(c,hardware);net_ids=[]
            for connection in c.get('connections',[]):
                net='projection:'+connection['source']+'->'+connection['target']
                if net not in hardware['nets']:
                    pos=hardware['placement_reference']['positions_um'];a,b=pos[connection['source']],pos[connection['target']]
                    distance=sum(abs(x-y) for x,y in zip(a,b))
                    hardware['nets'][net]={'cost':distance*sum(s['width_bits'] for s in connection['signals']),
                                           'scope':'original layout Manhattan bit-length proxy, not routed mod timing'}
                    wire_by_net[net]={'connections':[connection]}
                if net not in net_ids:net_ids.append(net)
            groups=c.get('groups',[c.get('group')])
            resources=sorted({r for group in groups for r in hardware['resources'] if r.startswith(group+'.')})
            scratch={site:row['word']+row['words'] for site,row in c['srams'].items()}
            site=next(iter(scratch))
            b={'id':c['binding'],'site':site,'ticks':cost['work_units'],'resources':resources,'nets':net_ids,
               'scratch_words':scratch[site],'scratch_by_site':scratch,
               'external_read_words':(cost['read_bytes']+15)//16,'external_write_words':(cost['write_bytes']+15)//16}
            bindings.append(b);choice[(t['id'],b['id'])]=option
        dp_tasks.append({'id':t['id'],'after':sorted(ancestors[t['id']]),'bindings':bindings})
        if len(dp_tasks)%50==0:progress({'native_tasks_prepared':len(dp_tasks)})
    nets=list(wire_by_net)
    for i,n in enumerate(nets):
        for m in nets[i+1:]:
            try:merge(merge({},wire_by_net[n]),wire_by_net[m])
            except ValueError:hardware['incompatible_nets'].append([n,m])
    progress({'phase':'native_global_search','tasks':len(dp_tasks),'bindings':sum(len(t['bindings']) for t in dp_tasks)})
    plan=search(dp_tasks,hardware,width=width,ready_limit=4,wire_lookahead=False)
    if plan['status']!='planned':raise ValueError('native frontier failed: '+str(plan))
    proof=verify(dp_tasks,hardware,plan)
    # Re-encode only selected implementations with monotone deployment identities.
    ids=dict(test_ids);selected=[];all_calls=[];task_ends={};resource_ends={}
    resource_by={(t['id'],b['id']):b['resources'] for t in dp_tasks for b in t['bindings']}
    for row in plan['tasks']:
        task=tasks_by[row['id']];c=attach_completion(encode(task,choice[(row['id'],row['binding'])],storage,hardware,ids))
        if 'next_identities' in c:ids=dict(c['next_identities'])
        elif 'next_session' in c:
            ids.update(first_session=c['next_session'],tensor=c['next_tensor'],record_sequence_base=c['next_record_sequence'])
            ids['rf_object_base']+=sum(tile['write']['elements']//8 for tile in task['tiles'])
        resources=resource_by[(row['id'],row['binding'])]
        external=set().union(*(task_ends[p] for p in ancestors[row['id']]))
        external.update(i for r in resources for i in resource_ends.get(r,()))
        base=len(all_calls)
        for call in c['calls']:
            x=dict(call);x['index']=base+call['index'];x['source_task']=row['id']
            x['after']=[base+i for i in call['after']] if call['after'] else sorted(external)
            for edge in ('completion_after','requires_started'):
                if edge in call:x[edge]=[base+i for i in call[edge]]
            all_calls.append(x)
        depended={i for call in c['calls'] for i in call['after']}
        terminals={base+i for i in range(len(c['calls'])) if i not in depended}
        task_ends[row['id']]=terminals
        for r in resources:resource_ends[r]=terminals
        selected.append({'source_task':c['source_task'],'binding':c['binding'],'connections':c.get('connections',[]),
                         'first_call':base,'call_count':len(c['calls'])})
    fingerprint=digest({'graph':graph['source_model_sha256'],'hardware':digest(hardware),'selected':selected,'calls':all_calls,'storage':storage})
    return {'architecture_accepted':False,'diagnostic_only':True,
            'architecture_rejection':'Legacy group resources and mandatory UP supply; whole graph migration pending',
            'schema':'native-whole-graph-plan/1','plan_sha256':fingerprint,'graph_sha256':graph['source_model_sha256'],
            'hardware_instances':hardware['instance_order'],'selection':selected,'calls':all_calls,
            'storage':storage,'wiring':selected_plan(selected),'search_plan':plan,'search_verification':proof,
            'search_tasks':dp_tasks,'search_hardware':hardware,
            'view_aliases':{t['id']:t['alias'] for t in recipes['tasks'] if t['kind']=='View'},
            'timing_scope':'uncalibrated work-unit ranking; completion-driven executable order; TLM performance pending',
            'delivery_accepted':False}
