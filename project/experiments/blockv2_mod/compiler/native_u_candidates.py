"""Encode U implementations from allocated graph operands, not stage archives.

A candidate owns its private SRAM for this sequence. The scheduler may overlap
other instances; per-call completion dependencies remain explicit.
"""
from native_backend import NativeBackend
from native_p_candidates import _storage
from native_transfer_program import load,store
from native_add_descriptor import add_provider
from native_rms_descriptor import rms_provider,q16_rms_profile

def candidate(task, *, group, regions, profile):
    if task['kind'] not in ('RMSNorm','Add'):raise ValueError('not a U arithmetic recipe')
    backend=NativeBackend(profile);site=group+'.S';calls=[]
    for tile_index,tile in enumerate(task['tiles']):
        for access in tile['read']:_storage(regions[access['root']],access['root'],-16)
        _storage(regions[tile['write']['value']],tile['write']['value'],-16)
        if len(tile['read'])!=2:raise ValueError('two arithmetic operands required')
        width=tile['write']['elements'];size=width*4
        if size>8192 or size%16 or any(a['elements']!=width for a in tile['read']):
            raise ValueError('arithmetic operands exceed U row/layout')
        if task['kind']=='RMSNorm':
            if width!=2048 or tile['reduction_elements']!=width:raise ValueError('native RMS row unsupported')
            provider=rms_provider(schema=3,provider_abi=7,operation=3,topology=backend.topology,
                       site=site,x_word=0,output_word=0,**q16_rms_profile(float(tile['epsilon'])))
        else:
            provider=add_provider(schema=3,provider_abi=7,operation=2,topology=backend.topology,site=site)
        for access,word in zip(tile['read'],(0,512)):
            calls.extend(load(access,regions[access['root']],group=group,sram_word=word,backend=backend))
        command={'op':'EXEC','read':[{'site':site,'address':0,'bytes':size},
                 {'site':site,'address':8192,'bytes':size}],
                 'write':[{'site':site,'address':0,'bytes':size}],'required_completion':'service_done'}
        encoded=backend.encode_deployment_call(group,provider,command)
        calls.append({'target':encoded.target,'group':group,'direction':'compute',
                      'descriptor_hex':encoded.descriptor.hex(),'completion':encoded.completion,
                      'operator':task['kind'],'tile':tile_index})
        calls.extend(store(tile['write'],regions[tile['write']['value']],group=group,
                           sram_word=0,backend=backend))
    for i,call in enumerate(calls):
        call['index']=i;call['after']=[] if i==0 else [i-1]
    return {'source_task':task['id'],'binding':task['id']+'@'+group,'group':group,
            'calls':calls,'srams':{site:{'word':0,'words':1024}},
            'completion':'last_call_destination_commit_ack',
            'numeric_contract':'S32 inputs already quantized for the native service; RMS Q16 profile, ADD existing E32 policy',
            'scope':'allocated native candidate; timing admission and global choice still required'}
