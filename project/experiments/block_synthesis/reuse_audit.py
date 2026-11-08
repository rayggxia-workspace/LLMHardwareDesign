"""Recheck frozen whole-model plans with the current independent checkers."""
import argparse
import json
from pathlib import Path
from verify_loop_dp import verify
from verify_primitive_cost import verify as verify_cost


def main():
    p=argparse.ArgumentParser();p.add_argument('directory',type=Path);a=p.parse_args();checks={}
    for label in ('five-groups','nine-groups-count-experiment'):
        ir=json.loads((a.directory/(label+'-ir.json')).read_text());checks[label]={'cost':verify_cost(ir)}
        for mode in ('plan','baseline','all-spill'):
            plan=json.loads((a.directory/(label+'-'+mode+'.json')).read_text())
            tasks=ir.get('all_spill_reference_tasks',ir['tasks']) if mode=='all-spill' else ir['tasks']
            checks[label][mode]=verify(tasks,ir['hardware'],plan)
        if label.startswith('nine'):
            budget=json.loads((a.directory/'summary.json').read_text())['results'][1]['equal_wire_budget']['budget']
            checks[label]['budget']=verify(ir['tasks'],ir['hardware'],json.loads((a.directory/'nine-groups-budget-plan.json').read_text()),budget)
    print(json.dumps({'passed':True,'checks':checks}))


if __name__=='__main__':main()
