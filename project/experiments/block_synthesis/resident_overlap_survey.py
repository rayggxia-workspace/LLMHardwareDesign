"""Compare opt-in overlap with the unchanged complete resident action pool."""
import argparse
import hashlib
import json
from pathlib import Path
import time

from cover_frontier import search
from resident_overlap_bindings import variants_for
from verify_cover_frontier import verify as verify_plan
from verify_primitive_cost import verify as verify_original
from verify_resident_bindings import verify as verify_native


def run(ir,output,*,width=8,wire_budget=18,mode='dp',backbone=None):
    output=Path(output);output.mkdir(exist_ok=False)
    def save(name,value):(output/(name+'.json')).write_text(json.dumps(value,separators=(',',':'))+'\n')
    frozen=output/'source';frozen.mkdir()
    for file in Path(__file__).parent.glob('*.py'):(frozen/file.name).write_bytes(file.read_bytes())
    native=verify_original(ir);start=time.monotonic();variants_for(ir,width=width,mode=mode)
    registration_seconds=time.monotonic()-start
    qualifier=verify_native(ir);save('ir',ir);save('native-audit',qualifier)
    plans={};seconds={};audits={}
    for name,w,rank in (('greedy',1,'shared_tail'),('dp',width,'shared_tail'),
        ('hypergraph_greedy',1,'hypergraph_completion'),('hypergraph_dp',width,'hypergraph_completion')):
        start=time.monotonic()
        plans[name]=search(ir['tasks'],ir['hardware'],ir['resident_actions'],width=w,wire_budget=wire_budget,rank_policy=rank)
        seconds[name]=time.monotonic()-start
        if plans[name]['status']!='planned':raise ValueError('bounded overlap cover search failed')
        audits[name]=verify_plan(ir['tasks'],ir['hardware'],ir['resident_actions'],plans[name],wire_budget)
        save(name,plans[name]);print(json.dumps({'phase':name,'seconds':seconds[name],
            **{k:plans[name][k] for k in ('makespan','external_words','wire_cost','multi_task_decisions','expanded')}}),flush=True)
    strongest=min(('greedy','hypergraph_greedy'),key=lambda name:plans[name]['makespan'])
    for name,seed in (('strong_backbone_dp',plans[strongest]),*([('serial_backbone_dp',backbone)] if backbone else [])):
        start=time.monotonic()
        plans[name]=search(ir['tasks'],ir['hardware'],ir['resident_actions'],width=width,wire_budget=wire_budget,
                           rank_policy='hypergraph_completion',backbone=seed)
        seconds[name]=time.monotonic()-start
        audits[name]=verify_plan(ir['tasks'],ir['hardware'],ir['resident_actions'],plans[name],wire_budget);save(name,plans[name])
    selected=min(plans,key=lambda n:(plans[n]['makespan'],plans[n]['external_words'],plans[n]['wire_cost']))
    summary={'passed':True,'original_native_audit':native,'resident_native_audit':qualifier,'plan_audits':audits,
        'registration_seconds':registration_seconds,'mode':mode,'overlap_scope':ir['resident_overlap_scope'],
        'plans':{n:{k:p[k] for k in ('makespan','external_words','wire_cost','multi_task_decisions','expanded')} for n,p in plans.items()},
        'search_seconds':seconds,'selected':selected,'strongest_greedy':strongest,
        'same_pool_gain_fraction':1-plans[selected]['makespan']/plans[strongest]['makespan'],
        'scope':'source-closed cover and actor scheduling under declared virtual channel costs; finite-S numeric/protocol evidence separate from calibrated system performance'}
    save('summary',summary);save('selected',plans[selected]);print(json.dumps(summary),flush=True)
    return summary


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ('ir','output'):p.add_argument(name,type=Path)
    p.add_argument('--mode',choices=('greedy','dp'),default='dp');p.add_argument('--width',type=int,default=8)
    p.add_argument('--wire-budget',type=int,default=18);p.add_argument('--backbone',type=Path);a=p.parse_args()
    result=run(json.loads(a.ir.read_text()),a.output,width=a.width,wire_budget=a.wire_budget,mode=a.mode,
               backbone=json.loads(a.backbone.read_text()) if a.backbone else None)
    result['input_sha256']={str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in (a.ir,*([a.backbone] if a.backbone else []))}
    (a.output/'summary.json').write_text(json.dumps(result,separators=(',',':'))+'\n')
