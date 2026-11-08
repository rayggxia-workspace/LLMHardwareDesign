"""Independent loop schedule check; does not import the DP/search code."""
from collections import defaultdict


def verify(tasks,hardware,plan,wire_budget=None):
    def check(ok,message):
        if not ok:raise ValueError(message)
    check(plan.get('status')=='planned','loop plan is not successful')
    # Deliberately independent from search's conflict filter. A foreign or
    # corrupted plan must fail even if its conflicting users never overlap.
    incompatible=[]
    for pair in hardware.get('incompatible_nets',[]):
        check(isinstance(pair,(list,tuple)) and len(pair)==2,'invalid incompatible_nets pair')
        check(all(isinstance(n,str) and n in hardware['nets'] for n in pair) and pair[0]!=pair[1],
              'invalid incompatible_nets endpoints')
        incompatible.append(tuple(pair))
    rows={r['id']:r for r in plan['tasks']}
    check(len(rows)==len(plan['tasks'])==len(tasks),'loop task coverage differs')
    claims=defaultdict(list);storage=defaultdict(list);nets=set();traffic=0
    for t in tasks:
        check(t['id'] in rows,'missing loop task')
        row=rows[t['id']];matches=[b for b in t['bindings'] if b['id']==row['binding']]
        check(len(matches)==1,'unknown/ambiguous loop binding');b=matches[0]
        check(row['site']==b['site'] and row['start']>=0 and row['end']-row['start']==b['ticks'],'loop time/site mismatch')
        check(all(rows[p]['end']<=row['start'] for p in t.get('after',[])),'loop read before producer commit')
        for r in b['resources']:claims[r].append((row['start'],row['end'],1))
        for site,n in b.get('scratch_by_site',{b['site']:b['scratch_words']}).items():
            storage[site].append((row['start'],row['end'],n))
        check(all(n in hardware['nets'] for n in b['nets']),'unknown static connection demand')
        nets.update(b['nets']);traffic+=b['external_read_words']+b['external_write_words']
    def peak(intervals):
        events=[(a,n) for a,b,n in intervals]+[(b,-n) for a,b,n in intervals]
        live=high=0
        for _,delta in sorted(events):live+=delta;check(live>=0,'negative resource occupancy');high=max(high,live)
        check(live==0,'resource not released');return high
    for r,intervals in claims.items():check(peak(intervals)<=hardware['resources'][r],'loop resource contention '+r)
    peaks={site:peak(intervals) for site,intervals in storage.items()}
    for site,n in peaks.items():check(n<=hardware['sites'][site]['words'],'private S overflow '+site)
    physical=nets|{n for n,meta in hardware['nets'].items() if meta.get('fixed')}
    for left,right in incompatible:
        check(not (left in physical and right in physical),
              'incompatible static connection demands: '+left+' / '+right)
    cost=sum(hardware['nets'][n]['cost'] for n in nets if not hardware['nets'][n].get('fixed'))
    check(sorted(nets)==plan['nets'] and cost==plan['wire_cost'],'static union differs')
    check(wire_budget is None or cost<=wire_budget,'static connection budget exceeded')
    check(traffic==plan['external_words'],'external transfer count differs')
    check(max((r['end'] for r in rows.values()),default=0)==plan['makespan'],'loop makespan differs')
    return {'passed':True,'peak_words':peaks,'external_words':traffic,'static_nets':len(nets),
            'checked_static_conflict_pairs':len(incompatible),
            'scope':'independent streaming-loop schedule/resource check; kernel program proof is separate'}
