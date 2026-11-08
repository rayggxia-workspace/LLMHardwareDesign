"""Inspect #220 demands before supplying a resource-interface catalog.

This intentionally empty-catalog diagnostic is not an implementation gate.
Use flow.py with a supplied library for native/external/new-wire realization.
Mother-control capacity or memory implementation is outside this tool's scope.
"""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'block_synthesis'))
from route_contract import VERSION, from_plan
from native_inventory import sha


def audit(ir_path,plan_path,inventory_directory,output):
    ir_path,plan_path=Path(ir_path),Path(plan_path)
    ir=json.loads(ir_path.read_text());plan=json.loads(plan_path.read_text())
    request=from_plan(ir,plan,{'schema_version':VERSION,'demands':{}},
                      {'schema_version':VERSION,'base_id':'nine-group-product-not-exported',
                       'state':'candidate','endpoints':{}})
    output=Path(output);output.mkdir(parents=True,exist_ok=False)
    (output/'route-requirements.json').write_text(json.dumps(request,indent=2)+'\n')
    inventory={}
    for path in sorted(Path(inventory_directory).glob('*-inventory.json')):
        data=json.loads(path.read_text());terms=data['terms']
        signal={p:t for p,t in terms.items() if t['signal_type']=='SIGNAL'}
        no_m10=[p for p,t in signal.items() if not any(s['layer']=='metal10' for s in t['shapes'])]
        inventory[path.stem.split('-')[0]]={
            'inventory_sha256':sha(path),'top':data['top'],'independent_macros':len(data['macros']),
            'terminals':len(terms),'signal_terminals':len(signal),'signal_terminals_without_m10':len(no_m10),
            'examples_without_m10':no_m10[:12],'odb_sha256':data['files']['native/6_final.odb']['sha256']}
    report={'schema_version':'product-routing-readiness/1','synthesis_schedule_rechecked':True,
            'source_ir_sha256':sha(ir_path),'source_plan_sha256':sha(plan_path),
            'logical_bundles':plan['nets'],'selected_tasks':len(plan['tasks']),
            'request_status':request['status'],'unresolved':request['unresolved'],
            'independent_fixture_inventory':inventory,
            'product_routing_ready':False,'physical_qualified':False,
            'missing_inputs':['Resource-interface catalog is intentionally absent from this diagnostic'],
            'hardware_prerequisites_inferred':False,
            'next_tool':'flow.py with hash-bound supplied resource library and native/external/bit-signal declarations',
            'scope':'Empty-catalog inspection only; not a requirement to implement extra hardware before general routing'}
    (output/'readiness.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'tasks':len(plan['tasks']),'bundles':len(plan['nets']),
                      'status':request['status'],'unresolved':len(request['unresolved'])}))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('ir','plan','inventories','output'):p.add_argument(name,type=Path)
    a=p.parse_args();audit(a.ir,a.plan,a.inventories,a.output)
