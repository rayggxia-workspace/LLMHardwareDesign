"""Execute every element through an actual finite-S resident event program.

Whole arrays are simulator external/reference storage. Each iteration uses
the same bounded private-S addresses and explicitly charged cold loads/stores.
No host split, multiply, add, or free intermediate delivery is performed.
"""
import numpy as np

from full_integer import Q
from resident_replay import replay


def element(recipe,index):
    base=recipe['graph'];count=recipe['loop']['elements']
    if type(index)!=int or not 0<=index<count:raise ValueError('resident loop element outside extent')
    objects={};deltas={};final=set(base['primitive_outputs'].values())
    for key,o in base['objects'].items():
        delta=(index if o['kind']=='external' and recipe['loop']['sources'][o['tensor']]=='element'
               or key in final else 0)
        updated=o
        if delta:
            updated={**o,'external_address':o['external_address']+delta}
            if o['kind']=='external':updated['index']=index
        objects[key]=updated;deltas[key]=delta
    graph={**base,'objects':objects,'index':index}
    # Object keys are symbolic slots in this serial loop body. Their source
    # identities are the explicit (tensor,index) fields above, not the text of
    # the template key. Native/scratch slots are overwritten before reuse.
    events=[]
    for e in recipe['plan']['events']:
        d=deltas.get(e.get('record'),0)
        events.append({**e,'external_address':e['external_address']+d}
                      if d and e['op'] in ('LOAD','STORE') else e)
    return graph,{**recipe['plan'],'events':events}


class Execution:
    def __init__(self,program,recipes):
        self.nodes={n['id']:n for n in program['instructions']};self.first={};self.member={}
        self.pending={};self.rows=[]
        positions={n['id']:i for i,n in enumerate(program['instructions'])}
        for r in recipes:
            names=r['primitives'];members=set(names)
            if not members<=self.nodes.keys() or members&self.member.keys():raise ValueError('resident execution coverage differs')
            if names!=sorted(names,key=positions.get):raise ValueError('resident execution order differs')
            between=program['instructions'][positions[names[0]]:positions[names[-1]]+1]
            if any(n['id'] not in members and n['op']!='Constant' for n in between):
                raise ValueError('resident execution crosses an outside instruction')
            self.first[names[0]]=r;self.member.update(dict.fromkeys(names,names[0]))

    def step(self,node,values):
        name=node['id']
        if name not in self.member:return None
        if name in self.first:
            r=self.first[name];count=r['loop']['elements'];outputs={n:np.empty(count,dtype=np.int64) for n in r['primitives']}
            sources={}
            for o in r['graph']['objects'].values():
                if o['kind']=='external' and 'literal' not in o:
                    q=values[o['tensor']]
                    if not isinstance(q,Q) or q.mask is not None:raise ValueError('resident source needs an unmasked integer tensor')
                    sources[o['tensor']]=q.raw.reshape(-1)
            for index in range(count):
                graph,plan=element(r,index)
                inputs={(o['tensor'],o['index']):int(sources[o['tensor']][o['index']])
                    for o in graph['objects'].values() if o['kind']=='external' and 'literal' not in o}
                result=replay(graph,plan,inputs)['observed_native_outputs']
                for primitive,key in graph['primitive_outputs'].items():
                    word=result[key]&0xffffffff
                    outputs[primitive][index]=word-(1<<32) if word&(1<<31) else word
            for primitive,raw in outputs.items():
                n=self.nodes[primitive];self.pending[primitive]=Q(raw.reshape(n['shape']),n['exponent'])
            self.rows.append({'primitives':r['primitives'],'elements':count,
                'native_operations':count*len(r['graph']['operations']),
                'external_words':count*r['plan']['external_words']})
        if name not in self.pending:raise ValueError('resident result requested before loop completion')
        return self.pending.pop(name)

    def report(self):
        if self.pending or len(self.rows)!=len(self.first):raise ValueError('resident selected loops not fully executed')
        return {'passed':True,'loops':self.rows,'scope':'every selected loop element uses bounded SRAM/ACK replay; other instructions use the existing integer interpreter; not controller/DMA/SystemC/time/energy qualification'}
