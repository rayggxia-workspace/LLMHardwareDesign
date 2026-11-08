"""Recheck a real #220 plan and expose missing physical bindings, without guessing.

An empty catalog is intentional for this audit: accepted standalone fixtures do
not supply a product-level correspondence for #220's logical read/write services.
This report does not call missing input an algorithmic routing impossibility.
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
            'missing_inputs':['Checked logical-service to actual native-signal catalog',
                              'Single nine-group placed native ODB/netlist/GDS and endpoint export',
                              'Physical memory gateway replacing the virtual memory services'],
            'integration_to_verify':['Nine-target mother/control distribution (current accepted mother has two resident targets)',
                                     'Local PM hardware and distinct instance identities',
                                     'Whole-product PG/CTS, actual RC, original Liberty and 300MHz constraints'],
            'scope':'Reports missing product inputs; does not infer infeasibility or invalidate independently accepted fixtures'}
    (output/'readiness.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'tasks':len(plan['tasks']),'bundles':len(plan['nets']),
                      'status':request['status'],'unresolved':len(request['unresolved'])}))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('ir','plan','inventories','output'):p.add_argument(name,type=Path)
    a=p.parse_args();audit(a.ir,a.plan,a.inventories,a.output)
