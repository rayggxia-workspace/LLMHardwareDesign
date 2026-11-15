"""Graph storage and runtime assets independent of legacy block scheduling."""
from math import prod
from native_macro_ffn_candidates import workspace_requirements
from native_macro_attention_candidates import workspace_bytes as attention_workspace_bytes
from pack_native_projections import projection_size,ORDINARY

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
        if name in regions:raise ValueError('duplicate storage allocation '+name)
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
        kind=task['kind'];size=0
        if kind=='SwiGLUFFN':
            for name,spec in workspace_requirements(task).items():allocate(name,4*spec['elements'])
            size=4*max(max(t['hidden'],t['intermediate']) for t in task['tiles'])
        elif kind=='MatMul':size=4*max(t['read'][0]['elements'] for t in task['tiles'])
        elif kind=='Attention':size=attention_workspace_bytes(task)
        elif kind=='RMSNorm':size=512
        if size:workspaces[task['id']]=allocate(task['id']+':candidate_workspace',size)
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
    return {'regions':regions,'weights':weights,'candidate_workspaces':workspaces,
            'runtime_asset_requirements':requirements,'end_address':base,
            'scope':'static allocation and asset requirements; data images are not materialized'}
