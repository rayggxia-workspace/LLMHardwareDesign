"""Post-discovery stronger-greedy audit. Does not rewrite the frozen main table.

Same immediate wire objective, shortlist, LRU transition and hardware. Only ties
prefer evicting fewer bytes with future readers, then a less populated resource.
No lookahead or extra compute resource. Report separately from predeclared suite.
"""
from pathlib import Path
import argparse
from concurrent.futures import ProcessPoolExecutor
import json
import subprocess
import time

from .core import canonical
from .cli import new_output, code_hashes
from .search import Hardware, actions, advance, initial
from .search_model import transformer
from .search_check import replay
REPO=Path(__file__).resolve().parents[3]


def solve_tie(w,h):
    start=time.perf_counter();s=initial(w,h);plan=[];expanded=0
    while s.ready:
        options=actions(w,h,s,frontier=4);expanded+=len(options)
        if not options:raise ValueError('infeasible tie audit')
        def order(action):
            cost,i,r,child=action
            # Values used by the selected task move to the LRU tail, but other
            # live values absent from the child cache were actually evicted.
            future=~child.done
            lost=sum(w.values[v].size for v in s.caches[r]
                     if v not in child.caches[r] and w.user_masks[v]&future)
            occupied=sum(w.values[v].size for v in s.caches[r])
            return cost,lost,occupied,i,r
        _,i,r,_=min(options,key=order)
        s,entry=advance(w,h,s,i,r,True);plan.append(entry)
    return dict(method='greedy_live_eviction_tie',wire_bytes=s.cost,plan=plan,
                expanded=expanded,algorithm_seconds=time.perf_counter()-start)


def cell(config):
    w=transformer(**{k:config[k] for k in ['prefill','decode','layers','rows','columns']})
    h=Hardware(capacity=config['capacity'])
    result=solve_tie(w,h);proof=replay(w,h,result)
    proof['placements']={r:sum(e['resource']==r for e in result['plan']) for r in h.names}
    return dict(id=config['id'],proof=proof),dict(id=config['id'],seconds=result['algorithm_seconds'])


def run(output,workers=1):
    from .search_experiment import cases
    if not 1<=workers<=4:raise ValueError('1..4 workers')
    out=new_output(REPO,output)
    source=code_hashes()
    configs=[c for c in cases('full') if c['category']=='main']
    if workers==1:results=list(map(cell,configs))
    else:
        with ProcessPoolExecutor(max_workers=workers) as pool:results=list(pool.map(cell,configs))
    science=dict(schema='workload-search-tie-audit/1',
                 reason='Post-discovery check of first-instance tie bias; same original 12 main configurations',
                 results=[x[0] for x in results])
    (out/'science.json').write_bytes(canonical(science))
    (out/'runtime.json').write_bytes(canonical(dict(source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip(),
        source_sha256=source,results=[x[1] for x in results])))
    if source!=code_hashes():raise ValueError('source changed')
    print(json.dumps(dict(status='pass',cases=len(results),wire_bytes=sum(x[0]['proof']['wire_bytes'] for x in results))))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output-dir',required=True);p.add_argument('--workers',type=int,default=1)
    a=p.parse_args();run(a.output_dir,a.workers)
