"""Opt-in actor schedules inside a whole-union resident reservation.

Unchanged serial candidates remain. Outer tasks cannot borrow resources or S
inside the reservation, and elements still run serially through final ACK.
The input hardware determines instance qualification and channel contention.
"""
from copy import deepcopy

from resident_continuation import visits
from resident_overlap import binding_channels,build,digest,search
from verify_resident_overlap import verify


KIND='commuting-native-actors-v1'
RESERVATION='all-union-resources-through-final-ACK'


def variants_for(ir,*,width=8,mode='dp'):
    if mode not in ('greedy','dp'):raise ValueError('unknown resident overlap policy')
    if 'resident_overlap_scope' in ir:raise ValueError('resident overlap already registered')
    if not ir.get('resident_actions'):raise ValueError('source-qualified resident covers required')
    from verify_resident_bindings import verify as verify_base
    verify_base(ir,numeric=False)
    proofs={};cache={};schedule_cache={};added=cache_hits=0
    for action in ir['resident_actions']:
        generated=[]
        for binding in action['bindings']:
            spec=binding['resident_region'];key=spec['recipe'];recipe=ir['resident_recipes'][key]
            channels=binding_channels(recipe['plan'],ir['hardware'],spec['actor_map'])
            identity=(key,tuple(sorted(channels.items())))
            if identity not in cache:
                programs=recipe.get('continuation_loop',{}).get('programs',[recipe['plan']])
                counts=visits(recipe['continuation_loop']) if recipe.get('continuation_loop') else [recipe['loop']['elements']]
                bodies=[]
                for program in programs:
                    dag=build(recipe['graph'],program,channels)
                    # Only the exact scheduling problem is shared. Source and
                    # word identities remain bound to each independent DAG;
                    # all hazards, durations and actor/channel edges are keys.
                    shape=digest({field:dag[field] for field in ('nodes','streams','channel_by_actor')})
                    if shape in schedule_cache:
                        schedule={**schedule_cache[shape],'dag_sha256':digest(dag)};cache_hits+=1
                    else:
                        greedy=min((search(dag,width=1,policy=p) for p in ('makespan','critical_path')),key=lambda s:s['makespan'])
                        schedule=search(dag,width=width,backbone=greedy) if mode=='dp' else greedy
                        schedule_cache[shape]=schedule
                    verify(recipe['graph'],program,dag,schedule,channels)
                    bodies.append({'dag':dag,'schedule':schedule})
                proof={'kind':KIND,'base_recipe':key,'channel_by_actor':channels,'bodies':bodies,
                    'visits':counts,'total_ticks':sum(n*b['schedule']['makespan'] for n,b in zip(counts,bodies)),
                    'reservation':RESERVATION,'mode':mode}
                proof_key=digest(proof);proofs[proof_key]=proof;cache[identity]=proof_key
            proof_key=cache[identity];proof=proofs[proof_key]
            if proof['total_ticks']>=binding['ticks']:continue
            b=deepcopy(binding);b['id']+=';actor-overlap='+mode;b['ticks']=proof['total_ticks']
            b['resident_overlap']={'kind':KIND,'proof':proof_key,'reservation':RESERVATION}
            generated.append(b)
        action['bindings'].extend(generated);added+=len(generated)
    ir['resident_overlap_proofs']=proofs
    ir['resident_overlap_scope']={'kind':KIND,'added_bindings':added,'mode':mode,'width':width,
        'reservation':RESERVATION,'schedule_shapes':len(schedule_cache),'schedule_cache_hits':cache_hits,
        'scope':'identical actor streams and external traffic under declared channel costs',
        'excluded':'outside-task or inter-element overlap, arbitrary native reorder, full controller/DMA/physical/SystemC/energy/token/s'}
    return ir
