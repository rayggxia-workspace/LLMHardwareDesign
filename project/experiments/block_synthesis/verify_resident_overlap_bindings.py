"""Independently validate loop visits, actual rebinding and overlap proofs."""
import hashlib
import json

from memory import descriptor_ticks
from verify_resident_overlap import verify


def certificates(ir):
    proofs=ir.get('resident_overlap_proofs',{});audits={};h=ir['hardware']
    def digest(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    for key,p in proofs.items():
        if (digest(p)!=key or p['kind']!='commuting-native-actors-v1' or
            p['reservation']!='all-union-resources-through-final-ACK' or p['mode'] not in ('greedy','dp')):
            raise ValueError('resident overlap certificate identity differs')
        r=ir['resident_recipes'][p['base_recipe']];programs=r.get('continuation_loop',{}).get('programs',[r['plan']])
        count=r['loop']['elements'];n=len(programs);cycle=r.get('continuation_loop',{}).get('cycle_start')
        counts=[int(i<count) for i in range(n)]
        if count>n:
            if cycle is None:
                if n!=1 or r.get('continuation_loop'):raise ValueError('resident overlap loop cycle missing')
                counts=[count]
            else:
                if not 0<=cycle<n:raise ValueError('resident overlap loop cycle invalid')
                for i in range(cycle,n):counts[i]+=(count-n)//(n-cycle)+int(i-cycle<(count-n)%(n-cycle))
        if p['visits']!=counts or len(p['bodies'])!=n:raise ValueError('resident overlap loop visits differ')
        total=0
        for program,b,multiplier in zip(programs,p['bodies'],counts):
            audit=verify(r['graph'],program,b['dag'],b['schedule'],p['channel_by_actor'])
            total+=multiplier*audit['makespan']
        if total!=p['total_ticks']:raise ValueError('resident overlap loop cost differs')
        audits[key]={'total_ticks':total,'bodies':n}
    for action in ir['resident_actions']:
        for b in action['bindings']:
            if not b.get('resident_overlap'):continue
            spec=b['resident_overlap'];p=proofs[spec['proof']];r=ir['resident_recipes'][b['resident_region']['recipe']]
            if (spec['kind']!='commuting-native-actors-v1' or spec['reservation']!=p['reservation'] or
                p['base_recipe']!=b['resident_region']['recipe']):raise ValueError('resident overlap binding proof differs')
            expected={};sites=set()
            for old,new in b['resident_region']['actor_map'].items():
                a=r['plan']['actors'][old];m=h['leaf_inventory'][new];s=h['sites'][m['site']]
                role={'M':'P','E':'E'}.get(a['kind'])
                if (role is None or new not in h['tile_service_bindings'][role] or
                    a['words']!=m['words'] or a['words']!=s['words'] or m['site'] in sites or
                    a['stride']!=(8 if role=='P' else 1)):
                    raise ValueError('resident overlap actual instance/storage differs')
                sites.add(m['site'])
                if (a['load_ticks']!=descriptor_ticks(h['virtual_memory'],1,'load',m['io_write_ticks']) or
                    a['store_ticks']!=descriptor_ticks(h['virtual_memory'],1,'store',m['io_read_ticks'])):
                    raise ValueError('resident overlap actual descriptor differs')
                expected[old]=m['memory_group']%h['virtual_memory']['channels']
            if p['channel_by_actor']!=expected:raise ValueError('resident overlap actual channels differ')
    return audits
