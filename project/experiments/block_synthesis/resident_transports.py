"""Explicit candidate transports for exploratory finite-S dataflow search.

These contracts do not qualify any new P/U top-level path. They require real
source/destination SRAM clients and a holding/ACK service frozen into a base;
metal alone cannot supply that service. Default production registration never
passes a candidate catalog. Timing is supplied, never inferred from distance.
"""


def catalog(paths,actors):
    result={}
    for p in paths:
        if (p.get('kind')!='resident-transport-candidate-v1' or
            not isinstance(p.get('id'),str) or not p['id'] or p['id'] in result or
            p.get('source') not in actors or p.get('destination') not in actors or
            p['source']==p['destination'] or p.get('word_bits')!=128 or
            type(p.get('ticks'))!=int or p['ticks']<1 or
            p.get('protocol')!='reserved-sink/source-held-through-write-ack' or
            not isinstance(p.get('provenance'),str) or not p['provenance'] or
            not isinstance(p.get('nets'),list) or not p['nets'] or
            any(not isinstance(n,str) or not n for n in p['nets']) or len(set(p['nets']))!=len(p['nets']) or
            not isinstance(p.get('resources'),list) or not p['resources'] or
            any(not isinstance(n,str) or not n for n in p['resources']) or
            len(set(p['resources']))!=len(p['resources'])):
            raise ValueError('explicit finite-S candidate transport contract required')
        if actors[p['source']].get('site',p['source'])==actors[p['destination']].get('site',p['destination']):
            raise ValueError('transport actors must own distinct SRAMs')
        result[p['id']]=p
    return result


def event_contract(event,paths,actors):
    """Check full-word endpoint identity and actual completion obligations."""
    p=paths.get(event.get('path'))
    if (p is None or event.get('source_actor')!=p['source'] or event.get('actor')!=p['destination'] or
        event.get('wait_ack') is not True or event.get('source_hold_until_ack') is not True or
        event.get('sink_reserved') is not True):
        raise ValueError('resident transfer path/ownership/ACK contract differs')
    for name,key in ((p['source'],'source_address'),(p['destination'],'address')):
        address=event.get(key);a=actors[name]
        if type(address)!=int or not 0<=address<a['words'] or address%a['stride']:
            raise ValueError('resident transfer endpoint outside aligned finite SRAM')
    return p
