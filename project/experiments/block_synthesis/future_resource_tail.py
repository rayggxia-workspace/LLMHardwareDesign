"""Committed resource releases constrain unready tasks as well as ready ones.

For every pending task v, a completion obeys
  T >= min_legal_b earliest_optimistic_finish(b, committed_releases, 0)
       + max_child conditional_tail(child).
Its unknown input arrival and future contention are relaxed, not fabricated.
The maximum over pending tasks complements the existing ready-frontier bound.
Candidate profiles share a suffix index; no model/layer/instance is special.
"""
from functools import lru_cache


class PendingSuffix:
    """Maximum suffix among undone tasks, using small blocks of real task bits."""
    def __init__(self,rows):
        rows=sorted(rows,reverse=True);self.blocks=[rows[i:i+8] for i in range(0,len(rows),8)]
        self.base=1
        while self.base<len(self.blocks):self.base*=2
        self.tree=[0]*(2*self.base)
        for i,block in enumerate(self.blocks):
            for _,bit in block:self.tree[self.base+i]|=bit
        for i in range(self.base-1,0,-1):self.tree[i]=self.tree[2*i]|self.tree[2*i+1]

    def maximum(self,done):
        pending=~done
        if not self.tree[1]&pending:return None
        i=1
        while i<self.base:i=2*i if self.tree[2*i]&pending else 2*i+1
        return next(value for value,bit in self.blocks[i-self.base] if bit&pending)


class FutureResourceTail:
    def __init__(self,conditional,tasks,hardware):
        self.conditional=conditional;self.hardware=hardware
        self.names=tuple(t['id'] for t in tasks);self.bits=tuple(1<<i for i in range(len(tasks)))
        self.resources=tuple(sorted(hardware['resources']));self.resource_ids={r:i for i,r in enumerate(self.resources)}
        self.profile_for={};self.profile_names=[];self.groups=[];known={}
        for name in self.names:
            key=(conditional.resource_profile_for[name],conditional.window_profile_for[name])
            if key not in known:
                known[key]=len(known);self.groups.append(key);self.profile_names.append(name)
            self.profile_for[name]=known[key]
        self.calls=self.improved=self.skipped=self.lookups=0
        self.maximum_improvement=0
        self._table=lru_cache(maxsize=8)(self._make_table)
        self._suffix=lru_cache(maxsize=1024)(self._remaining_suffixes)
        self._finish=lru_cache(maxsize=16384)(self._profile_finish)

    def _make_table(self,nets):
        c=self.conditional;tail=c.get(nets);rows=[[] for _ in self.groups]
        possible=all(tail[name] is not None for name in self.names)
        if not possible:return None
        for name,bit in zip(self.names,self.bits):
            suffix=max((tail[child] for child in c.children[name]),default=0)
            rows[self.profile_for[name]].append((suffix,bit))
        prepared=[]
        for (profile,_),members in zip(self.groups,rows):
            options=[]
            for alternative,terms in c.resource_profiles[profile]:
                if not c.possible(nets|c.alternatives[alternative]):continue
                options.append(tuple((tuple(self.resource_ids[r] for r in group),ticks) for group,ticks in terms))
            if not options:return None
            indices=tuple(sorted({r for terms in options for group,_ in terms for r in group}))
            remap={r:i for i,r in enumerate(indices)}
            compact=tuple(tuple((tuple(remap[r] for r in group),ticks) for group,ticks in terms) for terms in options)
            minimum=min(max(ticks for _,ticks in terms) for terms in compact)
            prepared.append((PendingSuffix(members),indices,compact,minimum))
        return prepared

    def _remaining_suffixes(self,nets,done):
        table=self._table(nets)
        if table is None:return None
        return tuple(index.maximum(done) for index,_,_,_ in table)

    def _profile_finish(self,options,available):
        return min(max(max((available[r] for r in group),default=0)+ticks for group,ticks in terms)
                   for terms in options)

    def get(self,state,current_bound=None):
        self.calls+=1;nets=frozenset(state.nets);table=self._table(nets)
        if table is None:return None
        suffixes=self._suffix(nets,state.done)
        bound=state.makespan if current_bound is None else max(state.makespan,current_bound)
        before=bound
        available=tuple(min(state.resources[r]) for r in self.resources)
        # The suffix index excludes already scheduled nodes even when a node
        # left the dependency frontier long ago. Static nets remain selected.
        for i,suffix in sorted(enumerate(suffixes),key=lambda x:-1 if x[1] is None else x[1],reverse=True):
            if suffix is None:continue
            _,indices,options,minimum=table[i]
            local=tuple(available[r] for r in indices)
            # Choosing the minimum-duration option is one legal relaxation.
            # Its finish is <= max(all releases)+minimum; use this only as
            # an upper bound to skip evaluation, never as a lower bound.
            if not self.hardware.get('window_calendar') and max(local,default=0)+minimum+suffix<=bound:
                self.skipped+=1;continue
            self.lookups+=1
            if self.hardware.get('window_calendar'):
                finish=self.conditional.ready_finish(self.profile_names[i],nets,state.resources,0,windows=state.windows)
            else:finish=self._finish(options,local)
            if finish is None:return None
            bound=max(bound,finish+suffix)
        if bound>before:self.improved+=1;self.maximum_improvement=max(self.maximum_improvement,bound-before)
        return bound

    def statistics(self):
        return {'profiles':len(self.groups),'rank_calls':self.calls,'stronger_than_ready_bound':self.improved,
                'maximum_extra_bound_ticks':self.maximum_improvement,'profile_upper_bound_skips':self.skipped,
                'profile_finish_queries':self.lookups,'finish_cache':self._finish.cache_info()._asdict(),
                'suffix_cache':self._suffix.cache_info()._asdict(),
                'scope':'pending-task committed-release plus conditional descendant tail; relaxation, not an optimal schedule'}
