"""Projection candidates using explicitly selected M/S_P endpoints.

Segmented inputs are materialized by real load/store calls, never by a host
transpose. This lowerer requires registered native routes; it does not add them.
"""
from native_backend import NativeBackend
from native_p_candidates import _storage,row_transfer
from emit_static_projection import emit_projection
from projection_local_descriptor import encode

def candidate(task,*,binding,regions,weights,hardware,identities,workspace=None):
    if task['kind']!='MatMul':raise ValueError('not a projection recipe')
    if binding['service_module']!='projection_local_service_controller':
        raise ValueError('local-source service binding required')
    group=binding['control_owner'];macros=hardware['macro_instances']
    for role,master in (('m','m_native_leaf_s32'),('s','local_s_p')):
        instance=binding['resources'][role]
        if macros[instance]['master']!=master or macros[instance]['control_owner']!=group:
            raise ValueError('selected native macro/owner mismatch')
    if binding['connections_already_present']:
        raise ValueError('local macro membership does not establish product data wiring')
    backend=NativeBackend(hardware['native_dispatch_overlay'])
    ids=dict(identities);calls=[];packed=None
    tensor=ids['tensor'];sequence=ids['record_sequence_base'];rf=ids['rf_object_base']
    if any(type(ids[n]) is not int or not 0<ids[n]<2**32
           for n in ('job','epoch','tensor','version')):
        raise ValueError('invalid deployment identity')
    def append(call):
        call=dict(call,index=len(calls),after=[] if not calls else [len(calls)-1])
        calls.append(call)
    if workspace is not None:
        _storage(workspace,workspace['value'],-16)
        if workspace['base']%64 or any(
          workspace['base']<r['base']+r['bytes'] and r['base']<workspace['base']+workspace['bytes']
          for r in regions.values()):
            raise ValueError('projection packing workspace overlaps graph storage/alignment')
    for index,tile in enumerate(task['tiles']):
        access,=tile['read'];region=regions[access['root']]
        out=regions[tile['write']['value']]
        _storage(region,access['root'],-16);_storage(out,tile['write']['value'],-16)
        weight=weights[tile['weight']['value']];n,k=weight['shape']
        if access['elements']!=k or tile['weight']['k']!=k or not k or k%128 or k>=65536:
            raise ValueError('projection K contract')
        if tile['weight']['columns']!=128 or tile['write']['elements']!=128:
            raise ValueError('projection output tile contract')
        segments=access['segments'];covered=0
        for s in segments:
            lo,count=s['source_element'],s['elements']
            if s['destination_element']!=covered or lo<0 or count<=0 or (lo+count)*4>region['bytes']:
                raise ValueError('projection operand coverage/range')
            covered+=count
        if covered!=k:raise ValueError('projection operand incomplete')
        if len(segments)==1:
            address=region['base']+segments[0]['source_element']*4
        else:
            if workspace is None or workspace['bytes']<k*4:
                raise ValueError('segmented projection needs allocated DDR packing workspace')
            key=(access['root'],tuple((s['source_element'],s['elements']) for s in segments))
            if packed!=key:
                for s in segments:
                    if s['source_element']%128 or s['destination_element']%128 or s['elements']%128:
                        raise ValueError('packing requires registered subrow transfer for non-128 segments')
                    for offset in range(0,s['elements'],128):
                        append(row_transfer(backend,group,region,direction='load',sram_word=832,
                            offset=(s['source_element']+offset)*4,value=access['value']))
                        append(row_transfer(backend,group,workspace,direction='store',sram_word=832,
                            offset=(s['destination_element']+offset)*4,value=workspace['value']))
                packed=key
            address=workspace['base']
        key=(ids['job'],ids['epoch'],tensor+index,ids['version'])
        if key[2]>=2**32:raise ValueError('projection tensor identity overflow')
        parameters={'topology':backend.topology,'rf_object_base':rf+(tile['write']['element_offset']//n)*(n//8),
          'output_version':ids['version'],'record_sequence_base':sequence,'input_key':key,
          'input_s_word':880,'output_s_word':0}
        scope,_=emit_projection(weight,parameters,first_column=tile['weight']['first_column'])
        raw=encode(scope,source_address=address,source_word=832)
        call=backend.encode_deployment_call(group,('scope_committed',lambda _:raw),
                                           {'required_completion':'scope_committed'})
        append({'target':call.target,'group':group,'direction':'compute','operator':'MatMul',
                'tile':index,'descriptor_hex':raw.hex(),'completion':call.completion,
                'ddr_address':address,'input_bytes':k*4})
        append(row_transfer(backend,group,out,direction='store',sram_word=0,
                            offset=tile['write']['element_offset']*4,value=tile['write']['value']))
        sequence+=n//8*(k//128)
    ids.update(tensor=tensor+len(task['tiles']),record_sequence_base=sequence,
               rf_object_base=rf+sum(t['write']['elements']//8 for t in task['tiles']))
    result = {'source_task':task['id'],'binding':task['id']+'@'+group+'.local_source',
      'groups':[group],'calls':calls,'connections':list(binding['required_connections']),
      'required_macro_leases':list(binding['required_macro_leases']),
      'required_registered_adapters':list(binding['required_registered_adapters']),
      'required_controller':binding['controller_instance'],
      'srams':{binding['private_sram']:{'word':0,'words':896,
          'live_windows':[{'word':0,'words':32},{'word':832,'words':32},{'word':880,'words':16}]}},
      'workspace_bytes':0 if workspace is None else workspace['bytes'],
      'next_identities':ids,'completion':'last_output_DDR_commit',
      'scope':'native descriptor lowering; all transfer/DDR bindings and parent RTL admission still required'}
    from native_candidate_resources import admit
    return admit(result,hardware)
