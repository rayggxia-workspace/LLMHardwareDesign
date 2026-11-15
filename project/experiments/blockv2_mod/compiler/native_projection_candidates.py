"""Paired U supply/P projection candidates with real descriptor encoders.

Supply and P execution are concurrent children of the completed source loads.
Their joint completion precedes output consumption and scratch reuse.
"""
from native_backend import NativeBackend
from native_transfer_program import load
from native_p_candidates import row_transfer,_storage
from projection_feed_descriptor import encode as encode_feed
from projection_connections import binding as wire_binding
from emit_static_projection import emit_projection

def slice_access(access,begin,count):
    if not 0<=begin<begin+count<=access['elements']:raise ValueError('input K chunk range')
    segments=[]
    for s in access['segments']:
        lo=max(begin,s['destination_element']);hi=min(begin+count,s['destination_element']+s['elements'])
        if lo<hi:segments.append({'destination_element':lo-begin,
                                  'source_element':s['source_element']+lo-s['destination_element'],
                                  'elements':hi-lo})
    if sum(s['elements'] for s in segments)!=count:raise ValueError('input K chunk not covered')
    return {**access,'elements':count,'segments':segments}

def candidate(task,*,source,target,regions,weights,hardware,identities):
    if task['kind']!='MatMul':raise ValueError('not a projection recipe')
    backend=NativeBackend(hardware['native_dispatch_overlay']);calls=[]
    first=identities['first_session']
    generation=identities['generation'];job=identities['job'];epoch=identities['epoch']
    tensor=identities['tensor'];version=identities['version']
    if any(type(x) is not int or not 0<x<2**32 for x in (first,generation,job,epoch,tensor,version)):
        raise ValueError('projection identities must be assigned by deployment')
    session_cursor=first
    rf_base=identities['rf_object_base'];sequence=identities['record_sequence_base']
    previous=[];record_cursor=sequence
    for index,tile in enumerate(task['tiles']):
        access,=tile['read'];weight=weights[tile['weight']['value']]
        region=regions[access['root']];_storage(region,access['root'],-16)
        out=regions[tile['write']['value']];_storage(out,tile['write']['value'],-16)
        if access['elements']!=tile['weight']['k'] or not 0<access['elements']<65536 or access['elements']%128:
            raise ValueError('projection activation exceeds native K extent')
        if tile['weight']['columns']!=128 or tile['write']['elements']!=128:
            raise ValueError('native projection output transfer requires full 128-element tile')
        n,k=weight['shape']
        if k!=tile['weight']['k'] or not 0<=tile['weight']['first_column']<=n-128:
            raise ValueError('packed weight binding differs from graph')
        key=(job,epoch,tensor+index,version)
        if key[2]>=2**32:raise ValueError('source identity wraps')
        parameters={'topology':backend.topology,'rf_object_base':rf_base+(tile['write']['element_offset']//n)*(n//8),'output_version':version,
                    'record_sequence_base':record_cursor,'input_key':key,'input_s_word':880,'output_s_word':0}
        raw,meta=emit_projection(weight,parameters,first_column=tile['weight']['first_column'])
        if len(raw)!=128:raise ValueError('one tile must encode one P scope')
        p=backend.encode_deployment_call(target,('scope_committed',lambda _:raw),
                                          {'required_completion':'scope_committed'})
        p_index=None
        for k_begin in range(0,k,2048):
            chunk_elements=min(2048,k-k_begin)
            chunk=slice_access(access,k_begin,chunk_elements)
            for call in load(chunk,region,group=source,sram_word=0,backend=backend):
                call['index']=len(calls);call['after']=list(previous);calls.append(call);previous=[call['index']]
            if p_index is None:
                p_index=len(calls)
                calls.append({'index':p_index,'after':list(previous),'target':p.target,'group':target,
                              'direction':'compute','operator':'MatMul','tile':index,'descriptor_hex':raw.hex(),
                              'completion':p.completion})
            packed_key=int.from_bytes(b''.join(x.to_bytes(4,'big') for x in key),'big')
            feed=encode_feed(topology=backend.topology,source_word=0,scratch_word=512,destination_word=880,
                             elements=chunk_elements,input_key=packed_key,session=session_cursor,first_k=k_begin)
            session_cursor+=1
            u=backend.encode_deployment_call(source,('service_done',lambda _:feed),
                                             {'required_completion':'service_done'})
            u_index=len(calls)
            calls.append({'index':u_index,'after':list(previous),'target':u.target,'group':source,
                          'direction':'supply','operator':'MatMul','tile':index,'k_begin':k_begin,
                          'descriptor_hex':feed.hex(),'completion':u.completion})
            # P stays live while U reloads the next chunk; never wait on P here.
            previous=[u_index]
        previous=[p_index,u_index]
        call=row_transfer(backend,target,out,direction='store',sram_word=0,
                          offset=tile['write']['element_offset']*4,value=tile['write']['value'])
        call['index']=len(calls);call['after']=previous;calls.append(call);previous=[call['index']]
        record_cursor+=n//8*(k//128)
    wire=wire_binding(source,target,hardware)
    return {'source_task':task['id'],'binding':task['id']+'@'+source+'+'+target,
            'groups':[source,target],'calls':calls,'connections':[wire],
            'srams':{source+'.S':{'word':0,'words':528},target+'.S':{'word':0,'words':1024}},
            'identities':dict(identities),'next_session':session_cursor,
            'next_record_sequence':record_cursor,'next_tensor':tensor+len(task['tiles']),
            'completion':'last_P_output_DDR_commit',
            'scope':'allocated native projection candidate; deployment identities must be assigned in selected execution order'}
