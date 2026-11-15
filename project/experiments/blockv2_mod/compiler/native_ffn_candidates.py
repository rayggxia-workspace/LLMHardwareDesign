"""SwiGLU lowered to native matrix, G32 and matrix commands.

The recipe is derived from graph dimensions. All intermediates have explicit
DDR allocations; no external FFN fixture drives a stripe or phase signal.
"""
import struct,zlib
from native_projection_candidates import candidate as projection
from native_p_candidates import _storage,row_transfer
from native_backend import NativeBackend

def workspace_requirements(task):
    mid=task['tiles'][0]['intermediate'];rows=len(task['tiles'])
    return {task['id']+':native:'+part:{'elements':rows*mid,'element_bytes':4,'exponent':-16}
            for part in ('gate','up','mid')}

def candidate(task,*,source,target,regions,weights,hardware,identities):
    if task['kind']!='SwiGLUFFN' or not task['tiles']:raise ValueError('not a SwiGLU recipe')
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
        result=projection(synthetic,source=source,target=target,regions=regions,weights=weights,hardware=hardware,identities=state)
        append(part,result['calls']);connections.extend(result['connections'])
        state.update(first_session=result['next_session'],tensor=result['next_tensor'],
                     record_sequence_base=result['next_record_sequence'],
                     rf_object_base=state['rf_object_base']+rows*weights[synthetic['tiles'][0]['weight']['value']]['shape'][0]//8)
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
    return {'source_task':task['id'],'binding':task['id']+'@'+source+'+'+target,
            'groups':[source,target],'calls':calls,'connections':connections,
            'srams':{source+'.S':{'word':0,'words':528},target+'.S':{'word':0,'words':1024}},
            'workspaces':list(work),'next_identities':state,'completion':'last_Down_DDR_commit',
            'scope':'allocated FFN candidate using native commands only; global choice and runtime execution still required'}
