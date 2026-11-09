"""Optimistic min-max hypergraph completion for convex cover frontiers.

Each action is a hyperedge: outside producers finish, its native duration
elapses, and covered outputs commit together. The relaxation allows overlapping
choices and ignores contention/capacity/future cache misses. Unlike distributing
a cover's cost, it preserves the real dependency boundary of each service.
"""
import heapq

from service_bounds import optimistic_ticks


class Completion:
    def __init__(self,actions,hardware,ids,*,wire_budget=None,resource_releases=False):
        self.actions=actions;self.h=hardware;self.ids=ids;self.wire_budget=wire_budget
        self.fixed={n for n,m in hardware['nets'].items() if m.get('fixed')}
        self.conflicts=[frozenset(p) for p in hardware.get('incompatible_nets',())]
        self.options={};self.calls=0
        self.resource_releases=resource_releases
        self.calendar=set(hardware.get('window_calendar',{}).get('resources',()))
        self.meta=[]
        for a in actions:
            mask=sum(1<<ids[n] for n in a['covers'])
            self.meta.append((mask,a['boundary'],a['covers']))

    def durations(self,nets):
        if nets in self.options:return self.options[nets]
        result=[]
        for a in self.actions:
            legal={}
            for b in a['bindings']:
                union=nets|frozenset(b['nets']);physical=union|self.fixed
                if any(p<=physical for p in self.conflicts):continue
                if self.wire_budget is not None and sum(self.h['nets'][n]['cost'] for n in union-self.fixed)>self.wire_budget:continue
                # Ordinary services reserve their whole resource union. A
                # phased compound or offset service can use an auxiliary
                # resource later; ignoring its release is safely optimistic.
                release=(() if not self.resource_releases or 'phase_execution' in b or
                    'parallel_shards' in b or 'materialized_tile' in b else
                    tuple(sorted(r for r in b['resources'] if r not in self.calendar)))
                ticks=optimistic_ticks(b)
                legal[release]=min(legal.get(release,ticks),ticks)
            result.append(tuple(legal.items()))
        self.options[nets]=result;return result

    def get(self,state):
        self.calls+=1;durations=self.durations(state.nets)
        outgoing={n:[] for n in self.ids if not state.done&(1<<self.ids[n])}
        remaining={};arrival={};queue=[];finish={}
        available=getattr(state,'resources',{})
        def offer(i):
            at=min(max([arrival[i]]+[available.get(r,(0,))[0] for r in release])+ticks
                   for release,ticks in durations[i])
            for n in self.meta[i][2]:heapq.heappush(queue,(at,n))
        for i,(mask,parents,members) in enumerate(self.meta):
            if state.done&mask or not durations[i]:continue
            unknown=[n for n in parents if not state.done&(1<<self.ids[n])]
            remaining[i]=len(unknown)
            arrival[i]=max((state.frontier[n] for n in parents if state.done&(1<<self.ids[n])),default=0)
            for n in unknown:outgoing[n].append(i)
            if not unknown:offer(i)
        while queue:
            at,n=heapq.heappop(queue)
            if n in finish:continue
            finish[n]=at
            for i in outgoing[n]:
                remaining[i]-=1;arrival[i]=max(arrival[i],at)
                if not remaining[i]:offer(i)
        if len(finish)!=len(outgoing):return float('inf')
        return max([state.makespan,*finish.values()])
