"""Native P row services with explicit graph-derived transfers and KV packing."""
from math import isfinite
from native_backend import NativeBackend
from native_ddr_load_descriptor import ddr_load_provider
from native_ddr_store_descriptor import ddr_store_provider
from native_rope_descriptor import rope_provider
from native_attention_descriptor import attention_provider

def _storage(region, value, exponent):
    if region['value']!=value or region.get('element_bytes')!=4 or region.get('exponent')!=exponent:
        raise ValueError('native numerical storage binding differs from service contract')
    if type(region['base']) is not int or type(region['bytes']) is not int or region['base']<0 or region['bytes']<=0:
        raise ValueError('invalid native storage extent')

def row_transfer(backend,group,region,*,direction,sram_word,offset,value):
    if direction not in ('load','store') or offset<0 or offset+512>region['bytes']:
        raise ValueError('native row transfer outside allocation')
    site=group+'.S';address=region['base']+offset;route=group+'.DDR.'+direction
    provider=(ddr_load_provider(topology=backend.topology,site=site,route=route,
               regions=[(region['base'],region['bytes'])],payload_bytes=512) if direction=='load' else
              ddr_store_provider(topology=backend.topology,site=site,route=route,
               regions=[(region['base'],region['bytes'],region.get('tag_base',region['base']//64))],payload_bytes=512))
    local={'site':site,'address':16*sram_word,'bytes':512,'value':value}
    external={'site':'DDR','address':address,'bytes':512,'value':value}
    command={'op':'COPY','route':route,'roles':['receive' if direction=='load' else 'send'],
             'read':[external if direction=='load' else local],
             'write':[local if direction=='load' else external],'required_completion':'destination_commit_ack'}
    call=backend.encode_deployment_call(group,provider,command)
    return {'target':call.target,'group':group,'direction':direction,
            'descriptor_hex':call.descriptor.hex(),'completion':call.completion,
            'ddr_address':address,'byte_count':512,'sram_word':sram_word,'storage_value':region['value']}

def _row_source(access,regions,exponent):
    region=regions[access['root']];_storage(region,access['root'],exponent)
    if access['elements']!=128 or len(access['segments'])!=1:raise ValueError('P row service requires contiguous 128-element source')
    segment,=access['segments']
    if segment['destination_element']!=0 or segment['elements']!=128 or segment['source_element']<0:
        raise ValueError('invalid native row segment')
    offset=4*segment['source_element']
    if offset+512>region['bytes']:raise ValueError('row exceeds source storage')
    return region,offset

def _compute(backend,group,provider,command,kind,tile_index):
    call=backend.encode_deployment_call(group,provider,command)
    return {'target':call.target,'group':group,'direction':'compute','operator':kind,'tile':tile_index,
            'descriptor_hex':call.descriptor.hex(),'completion':call.completion}

def candidate(task,*,group,regions,profile,workspace=None):
    if task['kind'] not in ('RoPE','Attention'):raise ValueError('not a native P row recipe')
    backend=NativeBackend(profile);site=group+'.S';calls=[];packing={};workspace_used=0
    if workspace is not None:
        _storage(workspace,workspace['value'],-16)
        if workspace['base']%512 or workspace['bytes']%512:raise ValueError('KV packing allocation alignment')
        if any(workspace['base']<r['base']+r['bytes'] and r['base']<workspace['base']+workspace['bytes'] for r in regions.values()):
            raise ValueError('KV packing overlaps a live graph allocation')
    def load_row(access,word,exponent):
        region,offset=_row_source(access,regions,exponent)
        calls.append(row_transfer(backend,group,region,direction='load',sram_word=word,offset=offset,value=access['value']))
    def kv_base(rows):
        nonlocal workspace_used
        sources=[_row_source(a,regions,-16) for a in rows]
        if not sources:raise ValueError('empty KV prefix')
        addresses=[r['base']+offset for r,offset in sources]
        if all(addr==addresses[0]+512*i for i,addr in enumerate(addresses)):
            return addresses[0]
        key=tuple((a['root'],offset) for a,(_,offset) in zip(rows,sources))
        if key in packing:return packing[key]
        size=512*len(rows)
        if workspace is None or workspace_used+size>workspace['bytes']:raise ValueError('candidate requires declared KV packing storage')
        base=workspace['base']+workspace_used
        for i,(a,(region,offset)) in enumerate(zip(rows,sources)):
            calls.append(row_transfer(backend,group,region,direction='load',sram_word=0,offset=offset,value=a['value']))
            calls.append(row_transfer(backend,group,workspace,direction='store',sram_word=0,
                                     offset=workspace_used+512*i,value=workspace['value']))
        workspace_used+=size;packing[key]=base
        return base
    for index,tile in enumerate(task['tiles']):
        write=tile['write'];out=regions[write['value']]
        _storage(out,write['value'],-16)
        if write['elements']!=128:raise ValueError('native output must be one 128-element row')
        if task['kind']=='RoPE':
            if len(tile['read'])!=3 or tile['elements']!=128 or tile['rotation']!='half-split':
                raise ValueError('RoPE geometry')
            names=[a['value'] for a in tile['read']]
            for a,word,exponent in zip(tile['read'],(0,32,64),(-16,-14,-14)):load_row(a,word,exponent)
            provider=rope_provider(topology=backend.topology,site=site,operands=names,result=write['value'],
                      shifts=(14,0,0,14,0,0),source_exponent=-16,native_exponent=-16,output_exponent=-16)
            cmd={'op':'EXEC','required_completion':'service_done',
                 'read':[{'value':v,'site':site,'address':word*16,'bytes':512} for v,word in zip(names,(0,32,64))],
                 'write':[{'value':write['value'],'site':site,'address':1536,'bytes':512}]}
            output_word=96
        else:
            if len(tile['read'])!=1 or not 0<tile['context']<=639 or tile['position']!=tile['context']-1:
                raise ValueError('Attention prefix')
            if len(tile['key_rows'])!=tile['context'] or len(tile['value_rows'])!=tile['context']:
                raise ValueError('Attention KV coverage')
            scale=tile['scale']
            if not isinstance(scale,(int,float)) or not isfinite(scale) or not 0<scale<=1:
                raise ValueError('Attention Q30 coefficient range')
            coefficient=round(scale*(1<<30))
            kb=kv_base(tile['key_rows']);vb=kv_base(tile['value_rows'])
            q=tile['read'][0];load_row(q,0,-16)
            provider=attention_provider(topology=backend.topology,site=site,query=q['value'],output=write['value'],
                context=tile['context'],position=tile['position'],coefficient=coefficient,
                key_base=kb,value_base=vb,score_byte=1024,work_byte=4096)
            cmd={'op':'EXEC','required_completion':'service_done',
                 'read':[{'value':q['value'],'site':site,'address':0,'bytes':512}],
                 'write':[{'value':write['value'],'site':site,'address':512,'bytes':512}]}
            output_word=32
        calls.append(_compute(backend,group,provider,cmd,task['kind'],index))
        calls.append(row_transfer(backend,group,out,direction='store',sram_word=output_word,
                                 offset=4*write['element_offset'],value=write['value']))
    for i,call in enumerate(calls):call['index']=i;call['after']=[] if i==0 else [i-1]
    return {'source_task':task['id'],'binding':task['id']+'@'+group,'group':group,'calls':calls,
            'srams':{site:{'word':0,'words':1024}},'workspace_bytes':workspace_used,
            'completion':'last_call_destination_commit_ack',
            'numeric_contract':'Q16 activation and Attention, Q14 RoPE trigonometric operands',
            'scope':'allocated native candidate; timing admission and global selection still required'}
