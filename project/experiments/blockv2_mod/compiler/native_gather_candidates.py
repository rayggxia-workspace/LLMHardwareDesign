"""Indexed embedding ingress encoded for the U descriptor-fetch frontend."""
import struct,zlib
from native_backend import NativeBackend
from native_transfer_program import store
from native_p_candidates import _storage

def candidate(task,*,group,regions,profile):
    if task['kind']!='Gather':raise ValueError('not an indexed ingress recipe')
    backend=NativeBackend(profile);calls=[];constraints=[]
    for index,tile in enumerate(task['tiles']):
        table=regions[tile['indexed_table']];_storage(table,tile['indexed_table'],-16)
        rows=tile['table_rows'];access,=tile['read'];indices=regions[access['root']]
        if tile['write']['elements']!=2048 or table['bytes']!=rows*8192 or not 0<rows<2**31:
            raise ValueError('Gather requires a declared 2048-element Q16 embedding table')
        if table['base']%128 or not 0<=table['base']<=(1<<48)-table['bytes']:
            raise ValueError('Gather table aperture')
        if indices.get('element_bytes')!=4 or indices.get('encoding')!='signed-int32-exact':
            raise ValueError('runtime index input needs an explicit exact INT32 binding')
        if access['elements']!=1 or len(access['segments'])!=1:
            raise ValueError('one runtime index required')
        segment,=access['segments']
        if segment['elements']!=1 or segment['destination_element']!=0:raise ValueError('Gather index view')
        offset=segment['source_element']*4
        if not 0<=offset<=indices['bytes']-4:raise ValueError('Gather index outside input')
        address=indices['base']+offset
        if address%4 or not 0<=address<1<<48:raise ValueError('Gather index aperture')
        raw=bytearray(128)
        # The legacy reserved index window is opposite destination bank zero;
        # flags=1 selects the actual DDR lookup instead of reading that window.
        struct.pack_into('<IHHIIQIHHQI',raw,0,0x31485447,128,1,0x02500002,backend.topology,
                         table['base'],rows,8192,0,address,1)
        struct.pack_into('<I',raw,124,zlib.crc32(raw[:124]))
        encoded=backend.encode_deployment_call(group,('destination_commit_ack',lambda _:bytes(raw)),
                                                 {'required_completion':'destination_commit_ack'})
        calls.append({'target':encoded.target,'group':group,'direction':'gather','tile':index,
                      'descriptor_hex':encoded.descriptor.hex(),'completion':encoded.completion})
        output=regions[tile['write']['value']];_storage(output,tile['write']['value'],-16)
        calls.extend(store(tile['write'],output,group=group,sram_word=0,backend=backend))
        constraints.append({'value':access['root'],'element':segment['source_element'],
                            'source_dtype':tile['index_dtype'],'native_encoding':'signed-int32-exact',
                            'minimum':-rows,'maximum':rows-1,
                            'enforcement':'runtime input materializer must check before encoding; no truncation'})
    for i,call in enumerate(calls):call['index']=i;call['after']=[] if i==0 else [i-1]
    return {'source_task':task['id'],'binding':task['id']+'@'+group,'group':group,'calls':calls,
            'runtime_input_constraints':constraints,'srams':{group+'.S':{'word':0,'words':512}},
            'completion':'last_call_destination_commit_ack',
            'scope':'allocated native ingress candidate with explicit runtime index constraints'}
