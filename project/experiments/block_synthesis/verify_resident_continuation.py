"""Check the entire generated continuation sequence without its planner.

Structural closure establishes which body follows which; finite-S replay
still has to establish each body's actual memory/bank postconditions.
"""
from resident_timing import audit


def verify(graph,loop,sequence,actors,zero,timing):
    if (sequence.get('kind')!='readonly-resident-loop-v1' or
        sequence.get('elements')!=loop['elements'] or type(sequence['elements'])!=int or sequence['elements']<1):
        raise ValueError('resident continuation kind/extent differs')
    expected=sorted(k for k,o in graph['objects'].items() if o['kind']=='constant' or
                    o['kind']=='external' and loop['sources'].get(o['tensor'])=='scalar')
    if sequence.get('persistent_records')!=expected:raise ValueError('resident loop invariant identity differs')
    programs=sequence['programs'];count=sequence['elements'];start=sequence['cycle_start']
    if not programs or len(programs)>count:raise ValueError('resident continuation program extent differs')
    if start is None:
        if len(programs)!=count:raise ValueError('resident continuation sequence is truncated')
    elif type(start)!=int or not 1<=start<len(programs):
        raise ValueError('resident continuation must begin with a charged cold program')
    for i,p in enumerate(programs):
        if (p['actors']!=actors or p['zero_address']!=zero or p['persistent_records']!=expected or
            p.get('initial_continuation')!=(None if i==0 else programs[i-1]['continuation'])):
            raise ValueError('resident continuation predecessor contract differs')
        if timing is not None:audit(p,timing)
    if start is not None and programs[start]['initial_continuation']!=programs[-1]['continuation']:
        raise ValueError('resident continuation cycle does not close')
    # Independent prefix/cycle multiplicities, including short final cycles.
    if start is None:multipliers=[1]*len(programs)
    else:
        turns,tail=divmod(count-start,len(programs)-start)
        multipliers=[1 if i<start else turns+int(i-start<tail) for i in range(len(programs))]
    fields=('copy_ticks','native_service_ticks','total_ticks','external_load_words','external_store_words','external_words')
    if any(p.get('transports') for p in programs):fields+=('transport_words','transport_ticks')
    total={f:sum(n*p[f] for n,p in zip(multipliers,programs)) for f in fields}
    if sequence['totals']!=total:raise ValueError('resident continuation finite-loop totals differ')
    return {'passed':True,'programs':len(programs),'program_visits':multipliers,'totals':total,
            'scope':'independent invariant, cold/prefix/cycle closure and event accounting; physical predecessor replay is separate'}
