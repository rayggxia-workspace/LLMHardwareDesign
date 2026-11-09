"""Register actual resident loops and compare one common graph-cover pool."""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import time

from cover_frontier import search
from resident_bindings import variants_for
from resident_timing import read_qualification
from verify_cover_frontier import verify as verify_plan
from verify_primitive_cost import verify as verify_original
from verify_resident_bindings import verify as verify_native


def run(ir,timing,output,*,width=8,wire_budget=18,backbone=None,cover_lengths=(),continuation=False,value_reuse=False):
    output=Path(output);output.mkdir(exist_ok=False)
    def save(name,value):(output/(name+'.json')).write_text(json.dumps(value,separators=(',',':'))+'\n')
    original_tasks=deepcopy(ir['tasks']);native=verify_original(ir)
    variants_for(ir,timing,width=width,cover_lengths=cover_lengths,continuation=continuation,value_reuse=value_reuse)
    if ir['tasks']!=original_tasks:raise ValueError('resident registration modified original action pool')
    qualifier=verify_native(ir);save('ir',ir);save('native-audit',qualifier)
    plans={};seconds={};audits={}
    for name,w,seed,rank in (('greedy',1,None,'shared_tail'),('dp',width,None,'shared_tail'),
        ('backbone_dp',width,'greedy','shared_tail'),('hypergraph_greedy',1,None,'hypergraph_completion'),
        ('hypergraph_dp',width,None,'hypergraph_completion'),('hypergraph_backbone_dp',width,'greedy','hypergraph_completion')):
        start=time.monotonic()
        plans[name]=search(ir['tasks'],ir['hardware'],ir['resident_actions'],width=w,wire_budget=wire_budget,
            backbone=plans[seed] if seed else None,rank_policy=rank)
        seconds[name]=time.monotonic()-start
        if plans[name]['status']!='planned':raise ValueError('bounded resident cover search failed')
        audits[name]=verify_plan(ir['tasks'],ir['hardware'],ir['resident_actions'],plans[name],wire_budget)
        save(name,plans[name]);print(json.dumps({'phase':name,'seconds':seconds[name],
            **{k:plans[name][k] for k in ('makespan','external_words','wire_cost','multi_task_decisions','expanded')}}),flush=True)
    if backbone is not None:
        start=time.monotonic();name='atomic_backbone_dp'
        plans[name]=search(ir['tasks'],ir['hardware'],ir['resident_actions'],width=width,wire_budget=wire_budget,backbone=backbone)
        seconds[name]=time.monotonic()-start;audits[name]=verify_plan(ir['tasks'],ir['hardware'],ir['resident_actions'],plans[name],wire_budget)
        save(name,plans[name])
    selected=min(plans,key=lambda n:(plans[n]['makespan'],plans[n]['external_words'],plans[n]['wire_cost']))
    strongest_greedy=min(('greedy','hypergraph_greedy'),key=lambda n:plans[n]['makespan'])
    summary={'passed':True,'original_native_audit':native,'resident_native_audit':qualifier,'plan_audits':audits,
        'plans':{n:{k:p[k] for k in ('makespan','external_words','wire_cost','multi_task_decisions','expanded')}
                 for n,p in plans.items()},'search_seconds':seconds,'selected':selected,
        'strongest_greedy':strongest_greedy,'same_pool_gain_fraction':1-plans[selected]['makespan']/plans[strongest_greedy]['makespan'],
        'rejected_regions':ir['resident_scope']['rejected'],
        'scope':'source-closed graph-cover candidates and independent native/finite-S/schedule audit; actual-weight full-loop selected replay, system timing/energy/token/s and physical remain separate'}
    save('summary',summary);save('selected',plans[selected]);print(json.dumps(summary),flush=True)
    return summary


def main():
    p=argparse.ArgumentParser()
    for name in ('ir','proof','output'):p.add_argument(name,type=Path)
    p.add_argument('--width',type=int,default=8);p.add_argument('--wire-budget',type=int,default=18)
    p.add_argument('--backbone',type=Path);p.add_argument('--cover-lengths',type=int,nargs='*',default=[])
    p.add_argument('--continuation',action='store_true');p.add_argument('--value-reuse',action='store_true');a=p.parse_args()
    timing=read_qualification(a.proof,[a.proof/('simulate-'+str(i)+'.log') for i in range(3)])
    summary=run(json.loads(a.ir.read_text()),timing,a.output,width=a.width,wire_budget=a.wire_budget,
                backbone=json.loads(a.backbone.read_text()) if a.backbone else None,cover_lengths=a.cover_lengths,
                continuation=a.continuation,value_reuse=a.value_reuse)
    summary['inputs_sha256']={str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in (a.ir,*([a.backbone] if a.backbone else []))}
    (a.output/'summary.json').write_text(json.dumps(summary,separators=(',',':'))+'\n')


if __name__=='__main__':main()
