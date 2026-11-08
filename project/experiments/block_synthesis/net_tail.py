"""State-conditioned relaxed remaining cost under the static wiring union.

Unlike a fixed per-node tail, an already selected physical net cannot be
forgotten at a layer boundary. Future bindings incompatible with that union or
its budget cannot supply optimistic tail costs. All-hit service endpoints and
ignored future contention still make this a relaxation, not a solution.
Equivalent operation/candidate profiles share work; cached results are keyed
by the actual net union, never by a model name or a layer number.
"""
from static_wiring import can_complete
from service_bounds import optimistic_ticks


class ConditionalTail:
    def __init__(self,tasks,hardware,children,reverse_order,*,fixed=frozenset(),
                 conflicts=(),wire_budget=None,completions=None):
        self.hardware=hardware;self.fixed=fixed;self.conflicts=conflicts
        self.budget=wire_budget;self.completions=completions
        self.children=children;self.order=tuple(reverse_order)
        self.alternatives=[];self.profile_for={};self.profiles=[]
        self.resource_profiles=[];self.resource_profile_for={}
        alternatives={};profiles={};resource_profiles={}
        for task in tasks:
            choices={};resource_choices=set()
            for b in task['bindings']:
                nets=frozenset(b['nets'])
                if nets not in alternatives:
                    alternatives[nets]=len(self.alternatives);self.alternatives.append(nets)
                i=alternatives[nets];cost=optimistic_ticks(b)
                choices[i]=min(choices.get(i,cost),cost)
                if 'phase_execution' in b or 'parallel_shards' not in b:
                    terms=((tuple(sorted(b['resources'])),cost),)
                elif 'frontier_partition' in b:
                    # Dynamic widths have not been chosen. Keep the declared
                    # optimistic duration without a false all-resource barrier.
                    terms=(((),cost),)
                else:
                    terms=tuple(sorted((tuple(sorted(c['binding']['resources'])),
                                        optimistic_ticks(c['binding'])) for c in b['parallel_shards']['children']))
                resource_choices.add((i,terms))
            signature=tuple(sorted(choices.items()))
            if signature not in profiles:
                profiles[signature]=len(self.profiles);self.profiles.append(signature)
            self.profile_for[task['id']]=profiles[signature]
            signature=tuple(sorted(resource_choices))
            if signature not in resource_profiles:
                resource_profiles[signature]=len(self.resource_profiles);self.resource_profiles.append(signature)
            self.resource_profile_for[task['id']]=resource_profiles[signature]
        self.cache={};self.feasible_cache={};self.hits=0;self.misses=0

    def possible(self,nets):
        if nets not in self.feasible_cache:
            physical=nets|self.fixed
            legal=not any(pair<=physical for pair in self.conflicts)
            if legal and self.budget is not None:
                cost=sum(self.hardware['nets'][n]['cost'] for n in nets
                         if not self.hardware['nets'][n].get('fixed'))
                legal=cost<=self.budget and can_complete(nets,self.hardware,self.completions,
                    self.budget,fixed=self.fixed,conflicts=self.conflicts)
            self.feasible_cache[nets]=legal
        return self.feasible_cache[nets]

    def get(self,nets):
        nets=frozenset(nets)
        if nets in self.cache:
            self.hits+=1;return self.cache[nets]
        self.misses+=1
        available=[self.possible(nets|candidate) for candidate in self.alternatives]
        lower=[]
        for profile in self.profiles:
            costs=[cost for i,cost in profile if available[i]]
            lower.append(min(costs) if costs else None)
        tail={}
        for name in self.order:
            own=lower[self.profile_for[name]]
            successors=[tail[c] for c in self.children[name]]
            tail[name]=None if own is None or any(x is None for x in successors) else own+max(successors,default=0)
        self.cache[nets]=tail
        return tail

    def statistics(self):
        return {'net_unions':len(self.cache),'cache_hits':self.hits,'cache_misses':self.misses,
                'candidate_net_sets':len(self.alternatives),'cost_profiles':len(self.profiles),
                'feasibility_unions':len(self.feasible_cache),'resource_profiles':len(self.resource_profiles)}

    def ready_finish(self,name,nets,resources,data_ready):
        """Earliest optimistic ready-task completion on append-only calendars.

        Future operations cannot move today's committed reservations earlier.
        Original serial children may start separately; only the explicit phase
        protocol has an all-union start barrier. Contention among future tasks,
        cold cache and serial child arbitration remain relaxed.
        """
        choices=[]
        for alternative,terms in self.resource_profiles[self.resource_profile_for[name]]:
            if not self.possible(nets|self.alternatives[alternative]):continue
            choices.append(max(max([data_ready]+[min(resources[r]) for r in group])+ticks
                               for group,ticks in terms))
        return min(choices) if choices else None
