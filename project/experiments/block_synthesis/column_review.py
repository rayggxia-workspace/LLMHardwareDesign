"""Same-hardware/same-budget audit of the common column action pool."""
import argparse
import hashlib
import json
from pathlib import Path
import time

from column_shards import variants_for
from loop_dp import optimize,search
from search_diagnostics import bounds
from utilization import report as utilization
from verify_loop_dp import verify
from verify_primitive_cost import verify as verify_cost


def main():
    p=argparse.ArgumentParser();p.add_argument('source',type=Path)
    p.add_argument('incumbents',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--scenario',default='nine-groups-count-experiment')
    p.add_argument('--width',type=int,default=8)
    a=p.parse_args();a.output.mkdir(exist_ok=False);label=a.scenario
    ir_path=a.source/(label+'-ir.json');ir=json.loads(ir_path.read_text())
    def fingerprint(value):return hashlib.sha256(json.dumps(value,sort_keys=True).encode()).hexdigest()
    before={k:fingerprint(ir[k]) for k in ('required_external_bytes','program','primitive_program',
                                          'operand_preparations','hardware')}
    variants_for(ir)
    if any(fingerprint(ir[k])!=v for k,v in before.items()):raise ValueError('column choices altered the shared arithmetic/hardware')
    cost=verify_cost(ir)
    output_ir=a.output/(label+'-ir.json');output_ir.write_text(json.dumps(ir,indent=2)+'\n')
    results=[];inputs={str(ir_path):hashlib.sha256(ir_path.read_bytes()).hexdigest()}
    budgets=sorted(int(f.stem.rsplit('-',1)[1]) for f in a.incumbents.glob(label+'-budget-*.json'))
    if not budgets:raise ValueError('same-budget incumbent inputs required')
    for budget in budgets:
        incumbent_path=a.incumbents/(label+'-budget-'+str(budget)+'.json')
        incumbent=json.loads(incumbent_path.read_text())
        inputs[str(incumbent_path)]=hashlib.sha256(incumbent_path.read_bytes()).hexdigest()
        verify(ir['tasks'],ir['hardware'],incumbent,wire_budget=budget)
        began=time.monotonic();base=search(ir['tasks'],ir['hardware'],width=1,wire_budget=budget)
        verify(ir['tasks'],ir['hardware'],base,wire_budget=budget)
        base_path=a.output/(label+'-greedy-'+str(budget)+'.json')
        base_path.write_text(json.dumps(base,indent=2)+'\n')
        print(json.dumps({'phase':'greedy','budget':budget,'makespan':base['makespan'],
                          'seconds':time.monotonic()-began}),flush=True)
        strong=search(ir['tasks'],ir['hardware'],width=1,ready_limit=1,wire_budget=budget,
                      priority='heft',rank_policy='earliest_finish')
        verify(ir['tasks'],ir['hardware'],strong,wire_budget=budget)
        (a.output/(label+'-heft-'+str(budget)+'.json')).write_text(json.dumps(strong,indent=2)+'\n')
        selected=optimize(ir['tasks'],ir['hardware'],width=a.width,wire_budget=budget,incumbents=[incumbent,base,strong])
        audit=verify(ir['tasks'],ir['hardware'],selected,wire_budget=budget)
        stem=label+'-budget-'+str(budget)
        (a.output/(stem+'.json')).write_text(json.dumps(selected,indent=2)+'\n')
        diagnostic=bounds(ir['tasks'],ir['hardware'],selected)
        (a.output/(stem+'-bound.json')).write_text(json.dumps(diagnostic,indent=2)+'\n')
        profile=utilization(ir,selected)
        (a.output/(stem+'-profile.json')).write_text(json.dumps(profile,indent=2)+'\n')
        bindings={t['id']:{b['id']:b for b in t['bindings']} for t in ir['tasks']}
        compounds=[bindings[r['id']][r['binding']] for r in selected['tasks']
                   if 'parallel_shards' in bindings[r['id']][r['binding']]]
        reference=min(incumbent['makespan'],base['makespan'],strong['makespan'])
        result={'scenario':label,'wire_budget':budget,'previous_dp':incumbent['makespan'],
            'same_pool_greedy':base['makespan'],'proposed':selected['makespan'],
            'same_pool_heft':strong['makespan'],
            'gain_against_stronger_baseline_fraction':1-selected['makespan']/reference,
            'change_against_previous_action_pool_fraction':1-selected['makespan']/incumbent['makespan'],
            'wire_cost':selected['wire_cost'],'external_words':selected['external_words'],
            'compound_tasks':len(compounds),'compound_services':sum(len(b['parallel_shards']['children']) for b in compounds),
            'audit':audit,'cost_audit':cost,'scope':ir['column_shard_scope'],
            'compile_seconds':time.monotonic()-began,'diagnostic':diagnostic,
            'performance_scope':'native-profile conservative model ticks; not system cycles or token/s'}
        results.append(result);print(json.dumps(result),flush=True)
        (a.output/'summary.json').write_text(json.dumps({'passed':True,'results':results,'inputs':inputs},indent=2)+'\n')


if __name__=='__main__':main()
