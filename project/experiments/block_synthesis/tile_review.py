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
    p.add_argument('--column-proof',type=Path);p.add_argument('--row-proof',type=Path)
    p.add_argument('--instance-services',type=Path)
    p.add_argument('--registered-ir',action='store_true')
    p.add_argument('--tile-partitions',action='store_true',help='common independent full-K native tile column partitions')
    p.add_argument('--tile-phase-partitions',action='store_true',help='also allow exact FCFS sharing among private-context tile children')
    p.add_argument('--materialized-windows',action='store_true',
        help='experimental packed/flag external materialization and actual auxiliary interval calendars')
    p.add_argument('--wire-budget',type=int,required=True);p.add_argument('--width',type=int,default=8)
    p.add_argument('--incumbent',type=Path);p.add_argument('--write-ir',action='store_true')
    p.add_argument('--incumbent-order',action='store_true',help='also search bindings on the checked incumbent order, for every baseline and DP policy')
    p.add_argument('--incumbent-backbone',action='store_true',help='also keep one replayed incumbent prefix inside the same DP beam budget')
    p.add_argument('--same-pool-baseline',type=Path,action='append',default=[])
    p.add_argument('--policies',nargs='+',choices=['greedy','old-dp','heft','conditional-greedy','conditional-dp','resource-greedy','resource-dp','price-greedy','price-dp'],
        default=['greedy','old-dp','heft','conditional-greedy','conditional-dp','resource-greedy','resource-dp'])
    a=p.parse_args()
    if a.registered_ir and any(x is not None for x in (a.column_proof,a.row_proof,a.instance_services)):
        raise ValueError('registered IR and new qualification inputs are mutually exclusive')
    if not a.registered_ir and (a.column_proof is None or a.instance_services is None):
        raise ValueError('proof and explicit instance service bindings required')
    if a.incumbent_order and a.incumbent is None:raise ValueError('incumbent order requires a checked incumbent')
    if a.incumbent_backbone and a.incumbent is None:raise ValueError('incumbent backbone requires a checked incumbent')
    a.output.mkdir(exist_ok=False)
    def write(name,value):
        (a.output/(name+'.json')).write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
    write('provenance',{'inputs':{str(f):hashlib.sha256(f.read_bytes()).hexdigest()
        for f in [a.ir]+([a.instance_services] if a.instance_services else [])+
                  ([a.incumbent] if a.incumbent else [])+a.same_pool_baseline},
        'module_sha256':{f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in Path(__file__).parent.glob('*.py')},
        'wire_budget':a.wire_budget,'width':a.width,'policies':a.policies})
    ir=json.loads(a.ir.read_text(encoding='utf-8'))
    before=json.dumps({k:v for k,v in ir['hardware'].items() if k not in ('tile_service_profiles','tile_service_bindings')},sort_keys=True,separators=(',',':'))
    if a.registered_ir:
        if 'tile_scope' not in ir or 'tile_service_profiles' not in ir['hardware']:
            raise ValueError('registered tile qualification missing')
        q=ir['hardware']['tile_service_profiles']
    else:
        q=read_qualification(a.column_proof,a.row_proof)
        variants_for(ir,q,service_bindings=json.loads(a.instance_services.read_text(encoding='utf-8')))
    write('qualification',q)
    after=json.dumps({k:v for k,v in ir['hardware'].items() if k not in ('tile_service_profiles','tile_service_bindings')},sort_keys=True,separators=(',',':'))
    if before!=after:raise ValueError('native tile recipe changed physical hardware')
    if a.tile_partitions or a.tile_phase_partitions:
        from tile_partitions import variants_for as register_partitions
        register_partitions(ir,phased=a.tile_phase_partitions)
    if a.materialized_windows:
        from materialized_tiles import variants_for as register_windows
        register_windows(ir)
    audit=verify_cost(ir);write('native-audit',audit)
    if a.write_ir:write('ir',ir)
    print(json.dumps({'phase':'native-audit-passed','tile_scope':ir['tile_scope']}),flush=True)
    plans={};times={};audits={}
    if a.incumbent:
        plans['old-pool-incumbent']=json.loads(a.incumbent.read_text(encoding='utf-8'))
        audits['old-pool-incumbent']=verify(ir['tasks'],ir['hardware'],plans['old-pool-incumbent'],wire_budget=a.wire_budget)
    for i,path in enumerate(a.same_pool_baseline):
        name='same-pool-baseline-'+str(i)
        plans[name]=json.loads(path.read_text(encoding='utf-8'))
        audits[name]=verify(ir['tasks'],ir['hardware'],plans[name],wire_budget=a.wire_budget)
    configurations={'greedy':{'width':1},'old-dp':{'width':a.width},
        'heft':{'width':1,'ready_limit':1,'priority':'heft','rank_policy':'earliest_finish'},
        'conditional-greedy':{'width':1,'rank_policy':'net_conditioned_tail'},
        'conditional-dp':{'width':a.width,'rank_policy':'net_conditioned_tail'},
        'resource-greedy':{'width':1,'rank_policy':'net_resource_tail'},
        'resource-dp':{'width':a.width,'rank_policy':'net_resource_tail'},
        'price-greedy':{'width':1,'rank_policy':'net_work_price'},
        'price-dp':{'width':a.width,'rank_policy':'net_work_price'}}
    runs=[(policy,configurations[policy]) for policy in a.policies]
    if a.incumbent_order:
        order=[r['id'] for r in plans['old-pool-incumbent']['tasks']]
        runs += [('ordered-'+policy,{**configurations[policy],'decision_order':order}) for policy in a.policies]
    if a.incumbent_backbone:
        runs += [('backbone-'+policy,{**configurations[policy],'backbone':plans['old-pool-incumbent']})
                 for policy in a.policies if configurations[policy]['width']>1]
    for policy,configuration in runs:
        start=time.monotonic()
        plan=search(ir['tasks'],ir['hardware'],wire_budget=a.wire_budget,**configuration)
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
    from column_shards import leaves
    chosen=[r['id'] for r in selected['tasks'] if any('dot_tile' in c for c in leaves(
        next(b for b in tasks[r['id']]['bindings'] if b['id']==r['binding'])))]
    baseline=min((v['makespan'] for k,v in plans.items() if k.removeprefix('ordered-') in ('old-pool-incumbent','greedy','old-dp','heft','resource-greedy','conditional-greedy','price-greedy') or k.startswith('same-pool-baseline-')),default=None)
    proposed=min((v['makespan'] for k,v in plans.items() if k.startswith('backbone-') or k.removeprefix('ordered-') in ('conditional-dp','resource-dp','price-dp')),default=None)
    result={'passed':True,'selected_source':name,'selected_tile_tasks':chosen,'tile_scope':ir['tile_scope'],
        'materialized_tile_scope':ir.get('materialized_tile_scope'),
        'tile_partition_scope':ir.get('tile_partition_scope'),
        'plans':{k:{f:v[f] for f in ('makespan','external_words','wire_cost')} for k,v in plans.items()},
        'search_seconds':times,'native_audit':audit,'plan_audits':audits,
        'same_pool_best_search_gain_fraction':1-proposed/baseline if proposed and baseline else None,
        'strongest_checked_baseline_ticks':baseline,
        'pool_common_baseline_gain_fraction':1-baseline/plans['old-pool-incumbent']['makespan'] if a.incumbent and baseline else None,
        'old_pool_to_new_plan_change_fraction':1-selected['makespan']/plans['old-pool-incumbent']['makespan'] if a.incumbent else None,
        'physical_hardware_sha256':hashlib.sha256(after.encode()).hexdigest(),
        'scope':'qualified native tile recipe and conservative descriptors; source graph scope unchanged; no new full-model numerical/SystemC/RTL/system/energy or token/s qualification'}
    write('summary',result);print(json.dumps(result),flush=True)


if __name__=='__main__':main()
