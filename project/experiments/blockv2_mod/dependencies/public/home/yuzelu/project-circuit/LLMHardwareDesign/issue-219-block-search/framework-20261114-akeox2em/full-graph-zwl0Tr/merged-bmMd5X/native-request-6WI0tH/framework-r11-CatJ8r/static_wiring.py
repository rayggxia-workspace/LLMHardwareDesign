"""Monotone static-net completion, independent of schedule/cache decisions.

Each task is an OR of possible net bundles. The product must satisfy every
task's clause, even when tasks execute in different layers. Return the complete
antichain of minimal wiring covers, or None on a bounded preprocessing cutoff.
An incomplete cover family must never be used to reject a DP state.
"""


def completion_covers(tasks,hardware,*,wire_budget,limit=4096):
    if limit<1:raise ValueError('positive static completion limit required')
    if wire_budget is None:return None
    fixed=frozenset(n for n,v in hardware['nets'].items() if v.get('fixed'))
    costs={n:v['cost'] for n,v in hardware['nets'].items()}
    if any(v<0 for v in costs.values()):return None
    conflicts=[frozenset(p) for p in hardware.get('incompatible_nets',[])]
    def cost(nets):return sum(costs[n] for n in nets-fixed)
    def legal(nets):return cost(nets)<=wire_budget and not any(p<=nets|fixed for p in conflicts)
    def antichain(options):
        result=[]
        for option in sorted(set(options),key=lambda x:(len(x),tuple(sorted(x)))):
            if not any(old<=option for old in result):result.append(option)
            if len(result)>limit:return None
        return result
    clauses=set()
    for task in tasks:
        options=antichain(frozenset(b['nets'])-fixed for b in task['bindings'] if legal(frozenset(b['nets'])))
        if options is None:return None
        if not options:return ()
        if frozenset() in options:continue
        clauses.add(tuple(options))
    covers=[frozenset()]
    for options in sorted(clauses,key=lambda x:(len(x),tuple(tuple(sorted(n)) for n in x))):
        expanded=set()
        for cover in covers:
            if any(option<=cover for option in options):expanded.add(cover)
            else:
                for option in options:
                    union=cover|option
                    if legal(union):expanded.add(union)
                    # Fall back conservatively instead of truncating covers.
                    if len(expanded)>limit:return None
        covers=antichain(expanded)
        if covers is None:return None
        if not covers:return ()
    return tuple(covers)


def can_complete(nets,hardware,covers,wire_budget,*,fixed=None,conflicts=None):
    """Check the future wiring union for this particular frontier's nets."""
    if covers is None:return True
    if fixed is None:fixed=frozenset(n for n,v in hardware['nets'].items() if v.get('fixed'))
    if conflicts is None:conflicts=tuple(frozenset(p) for p in hardware.get('incompatible_nets',[]))
    for cover in covers:
        union=nets|fixed|cover
        if any(p<=union for p in conflicts):continue
        cost=sum(hardware['nets'][n]['cost'] for n in union if not hardware['nets'][n].get('fixed'))
        if cost<=wire_budget:return True
    return False
