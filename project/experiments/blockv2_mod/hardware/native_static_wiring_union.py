"""One static product connection set for all phases; no metal time multiplexing."""
from native_selected_endpoint_bindings import build
def merge(bindings):
    base_ids={b.get('base_id') for b in bindings}
    base_hashes={b.get('base_rtl_contract_sha256') for b in bindings}
    if len(base_ids)!=1 or len(base_hashes)!=1:raise ValueError('different base revisions across phases')
    endpoints={};drivers={};connections={};constants={};unresolved={};sources={}
    for b in bindings:
        for name,row in b['endpoints'].items():
            if name in endpoints and endpoints[name]!=row:raise ValueError('phase endpoint mismatch: '+name)
            endpoints[name]=row
        for row in b['connections']:
            sink=row['sink'];value=('wire',row['driver'],row['shape'])
            if sink in drivers and drivers[sink]!=value:raise ValueError('static product multi-driver: '+sink)
            drivers[sink]=value;connections[sink]=row
        for row in b['constants']:
            sink=row['sink'];value=('constant',row['value'])
            if sink in drivers and drivers[sink]!=value:raise ValueError('static tie/wire conflict: '+sink)
            drivers[sink]=value;constants[sink]=row
        for row in b['unresolved']:unresolved[(row['instance'],row['kind'])]=row
        for name,h in b['sources'].items():
            if name in sources and sources[name]!=h:raise ValueError('phase RTL version mismatch: '+name)
            sources[name]=h
    return {'schema':'static-product-endpoint-union/1',
     'plan_sha256':[b['plan_sha256'] for b in bindings],'base_id':next(iter(base_ids)),
     'base_rtl_contract_sha256':next(iter(base_hashes)),
     'endpoints':endpoints,'connections':list(connections.values()),
     'constants':list(constants.values()),'unresolved':list(unresolved.values()),'sources':sources,
     'selected_known_connections_compatible':True,
     'physical_binding_complete':False,'execution_accepted':False,
     'scope':'union of known selected RTL endpoints; unresolved interfaces are not admitted as connected'}
