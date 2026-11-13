"""Optimistic compulsory copies from a resident frontier, not static ticks.

Ignore capacity, bank replacement, conflicts and placement restrictions within
a macro kind. Each record may be retained perfectly after its first arrival.
This is only a copy-cost bound for the serial resident-record action family.
"""


class FutureCopies:
    def __init__(self,graph,actors,*,transports=(),transport_net_budget=None):
        self.graph=graph;self.names=tuple(sorted(actors));self.meta=[actors[n] for n in self.names]
        self.by_kind={k:[i for i,m in enumerate(self.meta) if m['kind']==k] for k in ('M','E')}
        self.producer={n['output']:(i,n['kind']) for i,n in enumerate(graph['operations'])}
        self.external=set(graph['live_out'].values());self.profiles={};self.calls=0
        self.transports=tuple(transports)
        self.transport_net_budget=transport_net_budget

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
        transports=tuple(p for p in self.transports if self.transport_net_budget is None or
                         len(state.transport_nets|frozenset(p['nets']))<=self.transport_net_budget)
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
                arrival=[self.meta[a]['load_ticks'] for a in self.by_kind[kind]]
                # A compulsory kind arrival may now use a declared SRAM
                # transport. Ignore source availability and static capacity
                # only in this optimistic lower bound, never in transitions.
                arrival.extend(p['ticks'] for p in transports
                               if self.meta[self.names.index(p['destination'])]['kind']==kind)
                result+=min(arrival)
            # Initial external records already have a backing. A future
            # producer must create one if a different-kind consumer or live
            # output needs it. Existing dirty owners pay at most one STORE.
            if owner is None or record in state.backed:continue
            must_store=record in self.external or bool(missing)
            if transports and record not in self.external:
                # Not all remote consumers imply an external backing now.
                # Charge no speculative STORE; actual spills remain explicit.
                must_store=False
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


class FutureReuseCopies(FutureCopies):
    """Safe, deliberately weaker bound for optional repeated definitions.

    Only first-definition read-only arrivals and original output commits are
    compulsory. A repeated expression can run or be reused, so its operand
    copies and all transient spills are omitted from the optimistic bound.
    """
    def __init__(self,graph,actors,*,service_timing=None,**options):
        super().__init__(graph,actors,**options)
        self.timing=service_timing;self.first={};self.native_costs={}
        for i,n in enumerate(graph['operations']):self.first.setdefault(n['output'],i)

    def native_cost(self,n,term=None):
        from resident_timing import event_ticks
        key=n['id'],term
        if key not in self.native_costs:
            if n['kind']=='E':
                cost=event_ticks({'op':'E','opcode':n['opcode'],'shift':n['shift'],'inputs':n['inputs']},self.timing)
            else:
                cost=event_ticks({'op':'M_FINAL','width':n['width'],'shift':n['shift']},self.timing)
                cost+=max(0,len(n['terms'])-(term or 0))*min(event_ticks(
                    {'op':'M_TERM','k':n['k'],'reuse_b':reuse},self.timing) for reuse in (False,True))
            self.native_costs[key]=cost
        return self.native_costs[key]

    def profile(self,index,term=None):
        key=index,term
        if key in self.profiles:return self.profiles[key]
        uses={};pending_m=False
        for i,n in enumerate(self.graph['operations'][index:],index):
            if n.get('reuse_of'):continue
            if n['kind']=='M':
                terms=n['terms'][(term or 0):] if i==index else n['terms'];pending_m|=bool(terms)
                for t in terms:
                    for mode in ('a','b'):
                        if self.graph['objects'][t[mode]]['kind']!='produced':
                            uses.setdefault(t[mode],set()).add(('M',mode.upper()))
            else:
                for x in n['inputs']:
                    if self.graph['objects'][x]['kind']!='produced':uses.setdefault(x,set()).add(('E','input'))
        result=(tuple((x,frozenset(modes)) for x,modes in sorted(uses.items())),pending_m)
        self.profiles[key]=result;return result

    def bound(self,state,index,term=None):
        # The parent sees only read-only profile records, hence charges no
        # transient stores or optional-operation operands.
        result=super().bound(state,index,term)
        for commit in self.graph['external_commits']:
            value=commit['record']
            if commit['external_address']==self.graph['objects'][value]['external_address'] and value in state.backed:continue
            result+=min(a['store_ticks'] for a in self.meta)
        available=set(state.backed).union(*(set(row) for row in state.slots));charged=set()
        for i,n in enumerate(self.graph['operations'][index:],index):
            value=n['output']
            if not n.get('reuse_of') or value in charged or value in available or self.first[value]>=index:continue
            # No physical copy survives a previous definition. At least one
            # future repeated definition must execute its original command.
            # Do not recursively re-enter an open M accumulator; its consumed
            # terms are already paid and only its remaining service is due.
            result+=self.native_cost(n,term if i==index else None);charged.add(value)
        return result
