"""Real run161 final-function binding controls; deliberately corrupted copies."""
import argparse
import copy
import hashlib
import json
from pathlib import Path,PurePosixPath
from native_views import final_function_contract


def verify(results,out):
    assert not out.exists();cases={}
    for policy in 'AC':
        index=results/('run161'+policy.lower()+'-final-terminal/index.json')
        data=json.loads(index.read_text());artifacts=next(iter(data['tasks'].values()))['artifacts']
        proof=artifacts['native-final-function.json']['content']
        def accept(value):
            final_function_contract(value,PurePosixPath(proof['source']),proof['source_receipt_sha256'],policy,proof['original_flow_netlist_sha256'])
        accept(proof);faults={}
        for name in ['failed','wrong-source','wrong-policy','wrong-netlist','missing-initial','wrong-seed','short-scoreboard','failed-formal','wrong-physical-view']:
            bad=copy.deepcopy(proof)
            if name=='failed':bad['passed']=False
            if name=='wrong-source':bad['source']+='-different'
            if name=='wrong-policy':bad['policy']='C'if policy=='A'else'A'
            if name=='wrong-netlist':bad['original_flow_netlist_sha256']='0'*64
            if name=='missing-initial':del bad['initial_state_runs']['random-122']
            if name=='wrong-seed':bad['initial_state_runs']['random-121']['runtime_seed']=122
            if name=='short-scoreboard':bad['initial_state_runs']['all-ones']['scoreboard']['transactions']=241
            if name=='failed-formal':bad['formal']['checks']['explicit_unsat']=False
            if name=='wrong-physical-view':bad['formal']['physical_functional_view']['full_view_sha256']='0'*64
            try:accept(bad)
            except AssertionError:faults[name]=True
            else:raise AssertionError(name)
        cases[policy]=dict(actual_final_source_accepted=True,rejected_faults=faults,index_sha256=hashlib.sha256(index.read_bytes()).hexdigest())
    report=dict(passed=True,cases=cases,source_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest()for p in [Path(__file__),Path(__file__).with_name('native_views.py')]},
        scope='Source binding against actual immutable run161 final-function records and declared corruptions; no generated macro or boundary qualification')
    out.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(passed=True,actual_sources=len(cases),rejected_cases=18)))


if __name__=='__main__':
    parser=argparse.ArgumentParser(__doc__);parser.add_argument('results',type=Path);parser.add_argument('out',type=Path)
    args=parser.parse_args();verify(args.results,args.out)
