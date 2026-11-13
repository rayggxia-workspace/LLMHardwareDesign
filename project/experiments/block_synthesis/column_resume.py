"""Audit an immutable column IR and resume search without repeating lowering."""
import argparse
import hashlib
import json
from pathlib import Path
import time

from loop_dp import search
from search_diagnostics import bounds
from utilization import report as utilization
from verify_loop_dp import verify
from verify_primitive_cost import verify as verify_cost


def main():
    p=argparse.ArgumentParser();p.add_argument('ir',type=Path);p.add_argument('incumbent',type=Path)
    p.add_argument('greedy',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--outputs-from',type=Path);p.add_argument('--budget',type=int,required=True)
    p.add_argument('--width',type=int,default=8);a=p.parse_args();a.output.mkdir(exist_ok=False)
    def write(name,value):
        with (a.output/name).open('w',encoding='utf-8') as stream:json.dump(value,stream,indent=2)
    provenance={'module_sha256':{f.name:hashlib.sha256(f.read_bytes()).hexdigest()
                                for f in Path(__file__).parent.glob('*.py')},
                'inputs':{str(f):hashlib.sha256(f.read_bytes()).hexdigest()
                          for f in (a.ir,a.incumbent,a.greedy)}}
    ir=json.loads(a.ir.read_text())
    if a.outputs_from:
        # The first local diagnostic reused the slice driver, which renamed
        # the graph output to "last". Restore only the original output map;
        # no instruction, binding, storage or arithmetic is modified.
        outputs=json.loads(a.outputs_from.read_text())['primitive_program']['outputs']
        provenance['outputs_repair']={'source':str(a.outputs_from),
            'source_sha256':hashlib.sha256(a.outputs_from.read_bytes()).hexdigest(),
            'before':ir['primitive_program']['outputs'],'after':outputs}
        ir['primitive_program']['outputs']=outputs
    write('provenance.json',provenance)
    cost=verify_cost(ir);print(json.dumps({'phase':'native-audit-passed','bindings':cost['bindings']}),flush=True)
    if a.outputs_from:
        with (a.output/'ir.json').open('w',encoding='utf-8') as stream:json.dump(ir,stream,separators=(',',':'))
    choices=[]
    for label,path in (('previous-dp',a.incumbent),('same-pool-greedy',a.greedy)):
        plan=json.loads(path.read_text());verify(ir['tasks'],ir['hardware'],plan,wire_budget=a.budget)
        choices.append((label,plan))
    began=time.monotonic()
    strong=search(ir['tasks'],ir['hardware'],width=1,ready_limit=1,wire_budget=a.budget,
                  priority='heft',rank_policy='earliest_finish')
    verify(ir['tasks'],ir['hardware'],strong,wire_budget=a.budget);write('heft.json',strong)
    choices.append(('heft-append-only',strong));reference=min(p['makespan'] for _,p in choices)
    print(json.dumps({'phase':'heft-passed','makespan':strong['makespan']}),flush=True)
    plan=search(ir['tasks'],ir['hardware'],width=a.width,wire_budget=a.budget)
    audit=verify(ir['tasks'],ir['hardware'],plan,wire_budget=a.budget);write('frontier.json',plan)
    choices.append(('frontier',plan));source,selected=min(choices,key=lambda q:(q[1]['makespan'],q[1]['external_words'],q[1]['wire_cost']))
    write('selected.json',selected)
    diagnostic=bounds(ir['tasks'],ir['hardware'],selected);write('bounds.json',diagnostic)
    write('utilization.json',utilization(ir,selected))
    result={'passed':True,'wire_budget':a.budget,'selected_source':source,
        'candidates':{label:{k:p[k] for k in ('makespan','external_words','wire_cost')} for label,p in choices},
        'gain_against_stronger_baseline_fraction':1-selected['makespan']/reference,
        'native_audit':cost,'frontier_audit':audit,'diagnostic':diagnostic,
        'search_seconds':time.monotonic()-began,
        'scope':'same pool/resources/wire budget, conservative native model; no full-weight replay/system timing qualification'}
    write('summary.json',result);print(json.dumps(result),flush=True)


if __name__=='__main__':main()
