"""Same hardware/pool comparison with qualified native tile candidates.

Read proof directories, never a hand-edited timing table. Backend gains and
extra frontier-search gains have separate denominators. No system token/s.
"""
import argparse
import hashlib
import json
from pathlib import Path
import time

from loop_dp import search
from phase_accounting import account as phase_account
from tile_bindings import variants_for
from tile_recipe import read_qualification
from traffic_accounting import account as traffic_account
from utilization import report as utilization
from verify_loop_dp import verify
from verify_primitive_cost import verify as verify_cost


def main():
    p=argparse.ArgumentParser()
    p.add_argument('ir',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--column-proof',type=Path,required=True);p.add_argument('--row-proof',type=Path)
    p.add_argument('--instance-services',type=Path,required=True)
    p.add_argument('--wire-budget',type=int,required=True);p.add_argument('--width',type=int,default=8)
    p.add_argument('--incumbent',type=Path);p.add_argument('--write-ir',action='store_true')
    p.add_argument('--policies',nargs='+',choices=['greedy','old-dp','heft','conditional-greedy','conditional-dp'],
        default=['greedy','old-dp','heft','conditional-greedy','conditional-dp'])
    a=p.parse_args();a.output.mkdir(exist_ok=False)
    def write(name,value):
        (a.output/(name+'.json')).write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
    write('provenance',{'inputs':{str(f):hashlib.sha256(f.read_bytes()).hexdigest()
        for f in [a.ir,a.instance_services]+([a.incumbent] if a.incumbent else [])},
        'module_sha256':{f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in Path(__file__).parent.glob('*.py')},
        'wire_budget':a.wire_budget,'width':a.width,'policies':a.policies})
    ir=json.loads(a.ir.read_text(encoding='utf-8'))
    before=json.dumps(ir['hardware'],sort_keys=True,separators=(',',':'))
    q=read_qualification(a.column_proof,a.row_proof);write('qualification',q)
    variants_for(ir,q,service_bindings=json.loads(a.instance_services.read_text(encoding='utf-8')))
    after=json.dumps({k:v for k,v in ir['hardware'].items() if k not in ('tile_service_profiles','tile_service_bindings')},sort_keys=True,separators=(',',':'))
    if before!=after:raise ValueError('native tile recipe changed physical hardware')
    audit=verify_cost(ir);write('native-audit',audit)
    if a.write_ir:write('ir',ir)
    print(json.dumps({'phase':'native-audit-passed','tile_scope':ir['tile_scope']}),flush=True)
    plans={};times={};audits={}
    if a.incumbent:
        plans['old-pool-incumbent']=json.loads(a.incumbent.read_text(encoding='utf-8'))
        audits['old-pool-incumbent']=verify(ir['tasks'],ir['hardware'],plans['old-pool-incumbent'],wire_budget=a.wire_budget)
    configurations={'greedy':{'width':1},'old-dp':{'width':a.width},
        'heft':{'width':1,'ready_limit':1,'priority':'heft','rank_policy':'earliest_finish'},
        'conditional-greedy':{'width':1,'rank_policy':'net_conditioned_tail'},
        'conditional-dp':{'width':a.width,'rank_policy':'net_conditioned_tail'}}
    for policy in a.policies:
        start=time.monotonic()
        plan=search(ir['tasks'],ir['hardware'],wire_budget=a.wire_budget,**configurations[policy])
        times[policy]=time.monotonic()-start;write(policy,plan)
        if plan['status']!='planned':continue
        audits[policy]=verify(ir['tasks'],ir['hardware'],plan,wire_budget=a.wire_budget)
        plans[policy]=plan
        print(json.dumps({'phase':policy,'makespan':plan['makespan'],'search_seconds':times[policy]}),flush=True)
    if not plans:raise ValueError('no independently checked legal plan')
    name,selected=min(plans.items(),key=lambda x:(x[1]['makespan'],x[1]['external_words'],x[1]['wire_cost']))
    write('selected',selected)
    for label,operation in [('traffic',traffic_account),('utilization',utilization),('descriptor-demand',phase_account)]:
        write(label,operation(ir,selected))
    tasks={t['id']:t for t in ir['tasks']}
    chosen=[r['id'] for r in selected['tasks'] if 'dot_tile' in next(b for b in tasks[r['id']]['bindings'] if b['id']==r['binding'])]
    baseline=min((v['makespan'] for k,v in plans.items() if k in ('greedy','old-dp','heft')),default=None)
    proposed=min((v['makespan'] for k,v in plans.items() if k.startswith('conditional-')),default=None)
    result={'passed':True,'selected_source':name,'selected_tile_tasks':chosen,'tile_scope':ir['tile_scope'],
        'plans':{k:{f:v[f] for f in ('makespan','external_words','wire_cost')} for k,v in plans.items()},
        'search_seconds':times,'native_audit':audit,'plan_audits':audits,
        'same_pool_conditional_search_gain_fraction':1-proposed/baseline if proposed and baseline else None,
        'backend_gain_fraction':1-selected['makespan']/plans['old-pool-incumbent']['makespan'] if a.incumbent else None,
        'physical_hardware_sha256':hashlib.sha256(after.encode()).hexdigest(),
        'scope':'qualified native tile recipe and conservative descriptors; source graph scope unchanged; no new full-model numerical/SystemC/RTL/system/energy or token/s qualification'}
    write('summary',result);print(json.dumps(result),flush=True)


if __name__=='__main__':main()
