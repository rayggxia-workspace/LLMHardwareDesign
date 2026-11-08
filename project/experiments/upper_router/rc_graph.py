"""Distributed resistor graphs from completed, independently checked routes.

Wire resistance is evaluated between physical centerline nodes. Vias are
explicit resistors; overlapping/branched route edges are counted once. No
model, Block type, instance count or endpoint width is an algorithm constant.
Capacitance must come from an independently run extractor, not this module.
"""
import argparse
import json
import math
from pathlib import Path

from check import digest, verify
from geometry import need


def extract(spec, routes, *, dbu_per_micron, sheet_resistance_ohm, via_resistance_ohm):
    verify(spec,routes);need(not routes['failed'],'RC requires a completed route')
    need(type(dbu_per_micron) is int and dbu_per_micron>0,'invalid DBU')
    for value in (sheet_resistance_ohm,via_resistance_ohm):
        need(math.isfinite(value) and value>0,'positive finite R values required')
    graphs={};width=spec['technology']['width']
    for net in spec['nets']:
        r=routes['routes'][net['id']];edges={};ports={}
        def edge(a,b,resistance,kind):
            a,b=tuple(a),tuple(b)
            need(a!=b,'zero length resistor')
            key=tuple(sorted((a,b)))
            if key in edges:
                need(edges[key]==(resistance,kind),'conflicting physical edge')
            edges[key]=(resistance,kind)
        pitch=spec['technology']['pitch']
        for s in r['segments']:
            layer=int(s['layer'][1:]);a,b=s['a'],s['b']
            axis=0 if layer==11 else 1
            length=abs(b[axis]-a[axis]);need(length>0 and length%pitch==0,'off-grid segment')
            direction=1 if b[axis]>a[axis] else -1
            point=list(a)
            for _ in range(length//pitch):
                nxt=list(point);nxt[axis]+=direction*pitch
                edge((*point,layer),(*nxt,layer),sheet_resistance_ohm*pitch/width,'wire')
                point=nxt
        for p in r['via10']:
            a=(*p['at'],10);b=(*p['at'],11)
            edge(a,b,via_resistance_ohm,'via10');ports[p['pin']]=tuple(a)
        for p in r['via11']:
            edge((*p,11),(*p,12),via_resistance_ohm,'via11')
        expected=set([net['driver']]+net['sinks']) if net['sinks'] else set()
        need(set(ports)==expected,'RC terminal mismatch')
        nodes=sorted({p for ends in edges for p in ends})
        ids={p:i for i,p in enumerate(nodes)}
        adjacent={p:set() for p in nodes}
        for a,b in edges:adjacent[a].add(b);adjacent[b].add(a)
        visited=set();pending=nodes[:1]
        while pending:
            p=pending.pop()
            if p in visited:continue
            visited.add(p);pending.extend(adjacent[p]-visited)
        need(len(visited)==len(nodes),'disconnected resistor graph')
        graphs[net['id']]={'nodes':[{'id':i,'at_dbu':list(p[:2]),'layer':'M'+str(p[2])}
                                  for i,p in enumerate(nodes)],
                          'ports':{p:ids[n] for p,n in sorted(ports.items())},
                          'resistors':[{'a':ids[a],'b':ids[b],'ohm':value,'kind':kind}
                                       for (a,b),(value,kind) in sorted(edges.items())],
                          'wire_length_um':sum(abs(a[0]-b[0])+abs(a[1]-b[1])
                                               for (a,b),(v,k) in edges.items() if k=='wire')/dbu_per_micron}
    return {'schema_version':'upper-distributed-rc/1','spec_sha256':digest(spec),
            'routes_sha256':digest(routes),'dbu_per_micron':dbu_per_micron,
            'sheet_resistance_ohm':sheet_resistance_ohm,'via_resistance_ohm':via_resistance_ohm,
            'nets':graphs,'capacitance_status':'not_extracted','physical_qualified':False,
            'scope':'exact routed centerline R graph; geometry/electrical/field-C checks remain separate'}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('spec','routes','output'):p.add_argument(n,type=Path)
    p.add_argument('--dbu-per-micron',type=int,required=True)
    p.add_argument('--sheet-resistance-ohm',type=float,required=True)
    p.add_argument('--via-resistance-ohm',type=float,required=True)
    a=p.parse_args();read=lambda p:json.loads(p.read_text())
    result=extract(read(a.spec),read(a.routes),dbu_per_micron=a.dbu_per_micron,
                   sheet_resistance_ohm=a.sheet_resistance_ohm,via_resistance_ohm=a.via_resistance_ohm)
    with a.output.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
