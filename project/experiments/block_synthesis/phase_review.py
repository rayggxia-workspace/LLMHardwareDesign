"""Same-pool review of conditional static-network lookahead.

FCFS compound phases are a common backend, not credited as algorithm gain.
Original scalar/native arithmetic and the entire old action pool are retained.
No measured-system, full-weight, energy or token/s qualification is implied.
"""
import argparse
import hashlib
import json
from pathlib import Path
import time

from loop_dp import search
from phased_compounds import variants_for
from search_diagnostics import bounds
from utilization import report as utilization
from verify_loop_dp import verify
from verify_primitive_cost import verify as verify_cost
from phase_program import PhaseEventLimit


def main():
    p=argparse.ArgumentParser();p.add_argument('ir',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--incumbent',type=Path);p.add_argument('--wire-budget',type=int,required=True)
    p.add_argument('--width',type=int,default=8);p.add_argument('--write-ir',action='store_true')
    p.add_argument('--policies',nargs='+',choices=['greedy','old-dp','heft','conditional-greedy','conditional-dp','resource-greedy','resource-dp'],
                   default=['greedy','old-dp','heft','conditional-greedy','conditional-dp'])
    a=p.parse_args();a.output.mkdir(exist_ok=False)
    def write(name,value):
        with (a.output/(name+'.json')).open('w',encoding='utf-8') as stream:json.dump(value,stream,indent=2)
    provenance={'module_sha256':{f.name:hashlib.sha256(f.read_bytes()).hexdigest()
                                for f in Path(__file__).parent.glob('*.py')},
                'inputs':{str(f):hashlib.sha256(f.read_bytes()).hexdigest()
                          for f in [a.ir]+([a.incumbent] if a.incumbent else [])},
                'wire_budget':a.wire_budget,'width':a.width,'policies':a.policies}
    write('provenance',provenance)
    print(json.dumps({'phase':'loading'}),flush=True)
    ir=json.loads(a.ir.read_text(encoding='utf-8'))
    physical_before={k:v for k,v in ir['hardware'].items() if k!='phase_native_templates'}
    before=hashlib.sha256(json.dumps(physical_before,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    if 'phased_compound_scope' not in ir:variants_for(ir)
    physical={k:v for k,v in ir['hardware'].items() if k!='phase_native_templates'}
    after=hashlib.sha256(json.dumps(physical,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    if before!=after:raise ValueError('common phase backend changed physical hardware')
    cost=verify_cost(ir);write('native-audit',cost)
    if a.write_ir:
        with (a.output/'ir.json').open('w',encoding='utf-8') as stream:json.dump(ir,stream,separators=(',',':'))
    print(json.dumps({'phase':'native-audit-passed','tasks':len(ir['tasks']),
                      'phase_choices':ir['phased_compound_scope']['added_bindings']}),flush=True)
    choices={};timings={};audits={}
    if a.incumbent:
        choices['incumbent']=json.loads(a.incumbent.read_text(encoding='utf-8'))
        audits['incumbent']=verify(ir['tasks'],ir['hardware'],choices['incumbent'],wire_budget=a.wire_budget)
    configurations={
        'greedy':{'width':1},'old-dp':{'width':a.width},
        'heft':{'width':1,'ready_limit':1,'priority':'heft','rank_policy':'earliest_finish'},
        'conditional-greedy':{'width':1,'rank_policy':'net_conditioned_tail'},
        'conditional-dp':{'width':a.width,'rank_policy':'net_conditioned_tail'},
        'resource-greedy':{'width':1,'rank_policy':'net_resource_tail'},
        'resource-dp':{'width':a.width,'rank_policy':'net_resource_tail'}}
    for name in a.policies:
        began=time.monotonic()
        try:plan=search(ir['tasks'],ir['hardware'],wire_budget=a.wire_budget,**configurations[name])
        except PhaseEventLimit as error:
            write(name+'-failed-phase',error.diagnostic)
            raise
        timings[name]=time.monotonic()-began;write(name,plan)
        if plan['status']=='planned':
            audits[name]=verify(ir['tasks'],ir['hardware'],plan,wire_budget=a.wire_budget);choices[name]=plan
        print(json.dumps({'phase':name,'status':plan['status'],'makespan':plan.get('makespan'),
                          'search_seconds':timings[name]}),flush=True)
    if not choices:raise ValueError('no independently verified plan')
    source,selected=min(choices.items(),key=lambda q:(q[1]['makespan'],q[1]['external_words'],q[1]['wire_cost']))
    write('selected',selected);write('utilization',utilization(ir,selected));write('bounds',bounds(ir['tasks'],ir['hardware'],selected))
    baselines=[v['makespan'] for k,v in choices.items() if k in ('incumbent','greedy','old-dp','heft')]
    proposed=[v['makespan'] for k,v in choices.items() if k.startswith(('conditional-','resource-'))]
    result={'passed':True,'source':str(a.ir),'wire_budget':a.wire_budget,'selected_source':source,
        'candidates':{k:{f:v[f] for f in ('makespan','external_words','wire_cost','expanded','pruned')} for k,v in choices.items()},
        'search_seconds':timings,'native_audit':cost,'plan_audits':audits,
        'hardware_physical_fields_sha256':after,'phased_compound_scope':ir['phased_compound_scope'],
        'gain_against_strongest_tested_same_pool_baseline_fraction':1-min(proposed)/min(baselines) if proposed and baselines else None,
        'scope':'native-profile model; original scalar work/traffic, no tile; no full-weight/SystemC/RTL/physical/energy qualification'}
    write('summary',result);print(json.dumps(result),flush=True)


if __name__=='__main__':main()
