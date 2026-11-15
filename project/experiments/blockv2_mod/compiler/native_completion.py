"""Explicit start/completion edges for streamed P work and U supplies."""
from native_work_cost import fields

def attach(candidate):
    fields_by_name=fields();f=fields_by_name['input_key'];scopes={};feeds={}
    for call in candidate['calls']:
        raw=bytes.fromhex(call['descriptor_hex'])
        if int.from_bytes(raw[:4],'little')==0x02505001:
            key=int.from_bytes(raw[f[0]:f[0]+f[1]],'little')
            if key in scopes:raise ValueError('ambiguous streamed scope identity')
            scopes[key]=call
        elif int.from_bytes(raw[:4],'little')==0x44454650:
            key=int.from_bytes(raw[24:40],'little');feeds.setdefault(key,[]).append(call)
    if scopes.keys()!=feeds.keys():raise ValueError('P scope and U supply coverage differs')
    for key,p in scopes.items():
        group=feeds[key]
        p['completion_after']=[group[-1]['index']]
        for feed in group:feed['requires_started']=[p['index']]
    return candidate
