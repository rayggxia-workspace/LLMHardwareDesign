"""Audit stage fission against the shared prepared-kernel baseline."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

from loop_dp import optimize
from search_diagnostics import bounds
from utilization import report as utilization
from verify_loop_dp import verify
from verify_primitive_cost import verify as verify_cost


def main():
    p=argparse.ArgumentParser();p.add_argument('before',type=Path);p.add_argument('after',type=Path)
    p.add_argument('output',type=Path);a=p.parse_args();a.output.mkdir(exist_ok=False)
    def load(root,name):return json.loads((root/name).read_text())
    result=[];inputs={};known={}
    for label in ('five-groups','nine-groups-count-experiment'):
        old=load(a.before,label+'-ir.json');new=load(a.after,label+'-ir.json')
        for root in (a.before,a.after):
            for suffix in ('-ir.json','-plan.json','-baseline.json'):
                f=root/(label+suffix);inputs[str(f)]=hashlib.sha256(f.read_bytes()).hexdigest()
        if old['primitive_program']!=new['primitive_program'] or old['operand_preparations']!=new['operand_preparations']:
            raise ValueError('executed arithmetic/prepared operands changed')
        work=[]
        for ir in (old,new):
            total=Counter()
            for row in ir['program']:total.update(row.get('primitive_counts',{}))
            work.append(total)
        if work[0]!=work[1]:raise ValueError('native commands or traffic changed')
        old_plan=load(a.before,label+'-plan.json');old_base=load(a.before,label+'-baseline.json')
        plan=load(a.after,label+'-plan.json')
        base=load(a.after,label+'-baseline.json')
        old_audit=verify(old['tasks'],old['hardware'],old_plan)
        cost=verify_cost(new);verify(new['tasks'],new['hardware'],plan)
        verify(new['tasks'],new['hardware'],base)
        # Compare both the incumbent's connection budget and the new greedy's.
        budgets=sorted({old_plan['wire_cost'],old_base['wire_cost'],base['wire_cost']})
        equal={}
        for budget in budgets:
            incumbent=[known[budget]] if budget in known else []
            selected=optimize(new['tasks'],new['hardware'],width=8,wire_budget=budget,incumbents=incumbent)
            audit=verify(new['tasks'],new['hardware'],selected,wire_budget=budget)
            (a.output/(label+'-budget-'+str(budget)+'.json')).write_text(json.dumps(selected,indent=2)+'\n')
            equal[str(budget)]={'makespan':selected['makespan'],'wire_cost':selected['wire_cost'],'audit':audit,
                'selected_source':selected['selected_source'],'incumbent_count':selected['incumbent_count'],
                'search_statistics':selected['search_statistics']}
            known[budget]=selected
        diagnostic=bounds(new['tasks'],new['hardware'],plan)
        (a.output/(label+'-bound.json')).write_text(json.dumps(diagnostic,indent=2)+'\n')
        profile=utilization(new,plan)
        (a.output/(label+'-profile.json')).write_text(json.dumps(profile,indent=2)+'\n')
        result.append({'scenario':label,'old_strong_dp':old_plan['makespan'],'old_wire_cost':old_plan['wire_cost'],
            'stage_greedy':base['makespan'],'stage_greedy_wire_cost':base['wire_cost'],
            'stage_dp':plan['makespan'],'stage_dp_wire_cost':plan['wire_cost'],
            'same_pool_dp_gain_fraction':1-plan['makespan']/base['makespan'],
            'native_work_conserved':True,'native_totals':dict(work[1]),
            'equal_budget':equal,'old_audit':old_audit,'cost_audit':cost,
            'primitive_stage_scope':new['primitive_stage_scope'],
            'algorithm_target_credit':False,
            'reason':'stage fission is a shared capability; same-pool/same-budget search improvement must be assessed separately'})
        print(json.dumps(result[-1]),flush=True)
    (a.output/'summary.json').write_text(json.dumps({'passed':True,'results':result,'inputs':inputs,
        'scope':'native work/dependencies/resources/finite S/connection budgets; not system cycles or ASIC/FPGA comparison'},indent=2)+'\n')


if __name__=='__main__':main()
