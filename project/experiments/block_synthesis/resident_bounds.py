"""Optimistic compulsory copies from a resident frontier, not static ticks.

Ignore capacity, bank replacement, conflicts and placement restrictions within
a macro kind. Each record may be retained perfectly after its first arrival.
This is only a copy-cost bound for the serial resident-record action family.
"""


class FutureCopies:
    def __init__(self,graph,actors):
        self.graph=graph;self.names=tuple(sorted(actors));self.meta=[actors[n] for n in self.names]
        self.by_kind={k:[i for i,m in enumerate(self.meta) if m['kind']==k] for k in ('M','E')}
        self.producer={n['output']:(i,n['kind']) for i,n in enumerate(graph['operations'])}
        self.external=set(graph['live_out'].values());self.profiles={};self.calls=0

    def profile(self,index,term=None):
        key=index,term
        if key in self.profiles:return self.profiles[key]
        uses={};pending_m=False
        for i,n in enumerate(self.graph['operations'][index:],index):
            if n['kind']=='M':
                terms=n['terms'][(term or 0):] if i==index else n['terms']
                pending_m|=bool(terms)
                for t in terms:
                    uses.setdefault(t['a'],set()).add(('M','A'))
                    uses.setdefault(t['b'],set()).add(('M','B'))
            else:
                for x in n['inputs']:uses.setdefault(x,set()).add(('E','input'))
        result=(tuple((x,frozenset(uses.get(x,()))) for x in sorted(set(uses)|self.external)),pending_m)
        self.profiles[key]=result;return result

    def bound(self,state,index,term=None):
        self.calls+=1;profile,pending_m=self.profile(index,term)
        resident=[set(x for x in row if x is not None) for row in state.slots]
        result=0
        for record,uses in profile:
            owner=self.producer.get(record);unproduced=owner is not None and owner[0]>=index
            kinds={k for k,_ in uses};missing=set()
            for kind in kinds:
                sites=self.by_kind[kind]
                if any(record in resident[a] for a in sites):continue
                if kind=='M' and {mode for k,mode in uses if k=='M'}=={'B'} and any(
                        state.banks[a]==record for a in sites):continue
                if unproduced and owner[1]==kind:continue
                missing.add(kind)
            for kind in missing:
                result+=min(self.meta[a]['load_ticks'] for a in self.by_kind[kind])
            # Initial external records already have a backing. A future
            # producer must create one if a different-kind consumer or live
            # output needs it. Existing dirty owners pay at most one STORE.
            if owner is None or record in state.backed:continue
            must_store=record in self.external or bool(missing)
            if must_store:
                if unproduced:sites=self.by_kind[owner[1]]
                else:sites=[a for a,row in enumerate(resident) if record in row]
                if not sites:raise ValueError('compulsory copy bound lost a dirty record')
                result+=min(self.meta[a]['store_ticks'] for a in sites)
        if pending_m and not any(state.padding[a] for a in self.by_kind['M']):
            # At least one guarded A cell must be initialized before the next
            # feed. Ignore the second B cell and every later initialization.
            result+=7*min(self.meta[a]['load_ticks'] for a in self.by_kind['M'])
        return result
