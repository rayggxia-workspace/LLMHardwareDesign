"""SwiGLU lowered to native matrix, G32 and matrix commands.

The recipe is derived from graph dimensions. All intermediates have explicit
DDR allocations; no external FFN fixture drives a stripe or phase signal.
"""
import struct,zlib
from native_local_projection_candidates import candidate as projection
from native_p_candidates import _storage,row_transfer
from native_backend import NativeBackend

def workspace_requirements(task):
    mid=task['tiles'][0]['intermediate'];rows=len(task['tiles'])
    return {task['id']+':native:'+part:{'elements':rows*mid,'element_bytes':4,'exponent':-16}
            for part in ('gate','up','mid')}

def candidate(task,*,projection_binding,gated_binding,regions,weights,hardware,identities,workspace=None):
    if task['kind']!='SwiGLUFFN' or not task['tiles']:raise ValueError('not a SwiGLU recipe')
    target=gated_binding['control_owner']
    if gated_binding['service_module']!='gated_s32_service_controller':
        raise ValueError('explicit gated service binding required')
    g=hardware['macro_instances'][gated_binding['resources']['g']]
    if g['master']!='g_s32' or g['control_owner']!=target:
        raise ValueError('G32 resource mismatch')
    work=workspace_requirements(task);names=list(work);gate,up,mid_value=names
    for name,spec in work.items():
        _storage(regions[name],name,-16)
        if regions[name]['bytes']!=spec['elements']*4:raise ValueError('FFN temporary size')
    intervals=[(regions[n]['base'],regions[n]['base']+regions[n]['bytes'],n) for n in names]
    for low,high,name in intervals:
        if any(other!=name and low<r['base']+r['bytes'] and r['base']<high for other,r in regions.items()):
            raise ValueError('FFN temporary overlaps a live value')
    rows=len(task['tiles']);hidden=task['tiles'][0]['hidden'];middle=task['tiles'][0]['intermediate']
    if hidden%128 or middle%128:raise ValueError('native FFN tile geometry')
    backend=NativeBackend(hardware['native_dispatch_overlay']);site=target+'.S'
    state=dict(identities);calls=[];previous=[];connections=[]
    def append(part,sequence):
        nonlocal previous
        base=len(calls)
        for call in sequence:
            copy=dict(call);copy['recipe_part']=part;copy['index']=base+call['index']
            copy['after']=[base+i for i in call['after']] if call['after'] else list(previous)
            calls.append(copy)
        children={i for call in sequence for i in call['after']}
        previous=[base+i for i in range(len(sequence)) if i not in children]
    def matmul(part):
        synthetic={'id':task['id']+':'+part,'kind':'MatMul','tiles':[]}
        for row,tile in enumerate(task['tiles']):
            if tile['hidden']!=hidden or tile['intermediate']!=middle:raise ValueError('mixed FFN geometry')
            weight_name=tile['weights'][{'gate':0,'up':1,'down':2}[part]]
            n,k=weights[weight_name]['shape'];expected=(hidden,middle) if part=='down' else (middle,hidden)
            if (n,k)!=expected:raise ValueError('FFN packed matrix dimensions')
            access=tile['read'][0] if part!='down' else {
                'value':mid_value,'root':mid_value,'elements':middle,
                'segments':[{'destination_element':0,'source_element':row*middle,'elements':middle}]}
            destination={'gate':gate,'up':up}.get(part,tile['write']['value'])
            row_offset=row*n if part!='down' else tile['write']['element_offset']
            for first in range(0,n,128):
                synthetic['tiles'].append({'read':[access],'weight':{'value':weight_name,'k':k,
                  'first_column':first,'columns':128},'write':{'value':destination,'element_offset':row_offset+first,'elements':128}})
        result=projection(synthetic,binding=projection_binding,regions=regions,weights=weights,
                          hardware=hardware,identities=state,workspace=workspace)
        append(part,result['calls']);connections.extend(result['connections'])
        state.update(result['next_identities'])
    matmul('gate');matmul('up')
    gated_calls=[]
    for row in range(rows):
        for first in range(0,middle,128):
            offset=4*(row*middle+first)
            for name,word in ((gate,0),(up,32)):
                gated_calls.append(row_transfer(backend,target,regions[name],direction='load',sram_word=word,offset=offset,value=name))
            raw=bytearray(128)
            struct.pack_into('<IHHII4H',raw,0,0x314d5347,128,1,0x02500002,backend.topology,0,32,64,32)
            struct.pack_into('<I',raw,124,zlib.crc32(raw[:124]))
            encoded=backend.encode_deployment_call(target,('service_done',lambda _:bytes(raw)),
                                                    {'required_completion':'service_done'})
            gated_calls.append({'target':encoded.target,'group':target,'direction':'gated_compute',
                'descriptor_hex':encoded.descriptor.hex(),'completion':encoded.completion,'row':row,'first':first})
            gated_calls.append(row_transfer(backend,target,regions[mid_value],direction='store',sram_word=64,offset=offset,value=mid_value))
    for i,call in enumerate(gated_calls):call['index']=i;call['after']=[] if i==0 else [i-1]
    append('gated_activation',gated_calls);matmul('down')
    import json
    connections.extend(gated_binding['required_connections'])
    connections=list({json.dumps(c,sort_keys=True):c for c in connections}.values())
    p_owner=projection_binding['control_owner']
    srams={projection_binding['private_sram']:{'word':0,'words':896}}
    g_site=gated_binding['private_sram']
    if g_site not in srams:srams[g_site]={'word':0,'words':96}
    leases=set(projection_binding['required_macro_leases']+gated_binding['required_macro_leases'])
    leases.update(srams)
    result = {'source_task':task['id'],'binding':task['id']+'@M:'+p_owner+'@G:'+target,
            'groups':sorted({p_owner,target}),'calls':calls,'connections':connections,
            'required_macro_leases':sorted(leases),
            'required_registered_adapters':sorted(set(projection_binding['required_registered_adapters']+
                                                       gated_binding['required_registered_adapters'])),
            'srams':srams,'workspaces':list(work),'next_identities':state,
            'completion':'last_Down_DDR_commit',
            'scope':'graph-derived native FFN candidate with explicit M/G resources and DDR transfers; full plan admission pending'}
    from native_candidate_resources import admit
    return admit(result,hardware)
