"""Encode exact graph operand segments as counted native U transfer calls.

Storage comes from the selected plan/asset allocator. No implicit contiguous
copy, host transpose, dtype conversion or source-layout rewrite is performed.
"""
from native_transfer_descriptor import encode

def _region(region, value):
    if region['value']!=value or region['element_bytes']!=4:
        raise ValueError('native S32 transfer needs the selected source storage binding')
    if any(type(region[k]) is not int for k in ('base','bytes')) or region['base']<0 or region['bytes']<=0:
        raise ValueError('invalid source storage region')

def _call(backend, group, direction, region, sram_word, offset, size, tag):
    raw=encode(direction=direction,topology=backend.topology,sram_word=sram_word,
               address=region['base']+offset,byte_count=size,first_tag=tag)
    command={'op':'TRANSFER','required_completion':'destination_commit_ack'}
    call=backend.encode_deployment_call(group,('destination_commit_ack',lambda _:raw),command)
    return {'target':call.target,'group':group,'direction':direction,'descriptor_hex':call.descriptor.hex(),
            'sram_word':sram_word,'byte_count':size,'ddr_address':region['base']+offset,
            'completion':call.completion,'storage_value':region['value']}

def load(access, region, *, group, sram_word, backend):
    _region(region,access['root'])
    if type(sram_word) is not int or not 0<=sram_word<=1024:
        raise ValueError('SRAM window start')
    if not 0<access['elements']*4<=16384-sram_word*16:
        raise ValueError('operand does not fit selected SRAM window')
    result=[];covered=0
    for segment in access['segments']:
        logical,source,count=(segment[k] for k in ('destination_element','source_element','elements'))
        if any(type(x) is not int for x in (logical,source,count)) or logical!=covered or source<0 or count<=0:
            raise ValueError('invalid operand segment coverage')
        if (source+count)*4>region['bytes'] or logical%4:
            raise ValueError('operand segment outside storage/alignment')
        remaining=count*4;offset=source*4;word=sram_word+logical//4
        while remaining:
            size=min(8192,remaining)
            result.append(_call(backend,group,'load',region,word,offset,size,0))
            remaining-=size;offset+=size;word+=size//16
        covered+=count
    if covered!=access['elements']:raise ValueError('incomplete operand segment list')
    return result

def store(write, region, *, group, sram_word, backend, first_tag=None):
    _region(region,write['value'])
    count=write['elements'];offset=write['element_offset']*4
    if any(type(x) is not int for x in (count,offset,sram_word)) or count<=0 or offset<0 or offset+count*4>region['bytes']:
        raise ValueError('invalid output storage range')
    if not 0<=sram_word<=1024 or count*4>16384-sram_word*16:
        raise ValueError('output does not fit selected SRAM window')
    result=[];remaining=count*4;word=sram_word
    tag=region.get('tag_base',region['base']//64)+offset//64 if first_tag is None else first_tag
    while remaining:
        size=min(8192,remaining)
        result.append(_call(backend,group,'store',region,word,offset,size,tag))
        remaining-=size;offset+=size;word+=size//16;tag+=size//64
    return result
