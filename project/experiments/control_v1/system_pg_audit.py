"""Source-bound composition of actual upper PG and qualified native PG paths.

Requires the complete independently read-back GDS/ODB, not a route candidate.
This gate covers supply connectivity. Timing, function and electrical limits
remain separate mandatory composed-system gates.
"""
import copy,json
from pathlib import Path


def supply_graph(graph):
    expected=set(graph['instances'])
    for supply in ('VDD','VSS'):
        c=graph['connections']['PG_'+supply]
        assert c['driver']==dict(instance='TOP',pin=supply,direction='output')
        assert len(c['sinks'])==len(expected)
        assert {s['instance']for s in c['sinks']}==expected
        assert all(s['pin']==supply and s['direction']=='input'for s in c['sinks'])


def audit(manifest_path,graph_path,route,geometry,bind):
    for p in (manifest_path,graph_path,route/'receipt.json',geometry/'receipt.json'):bind(p)
    manifest=json.loads(manifest_path.read_text());graph=json.loads(graph_path.read_text())
    from boundary_links import validate
    bind(Path(__file__).with_name('boundary_links.py'));validate(manifest,graph);supply_graph(graph)
    candidate=json.loads((route/'receipt.json').read_text());assert candidate['passed']and not candidate.get('stage')
    assert candidate['search']['final_conflicts']==0 and candidate['search']['independent_tree_flood']
    physical=json.loads((geometry/'receipt.json').read_text())
    assert physical['passed']and physical['actual_odb_def_readback']and physical['actual_joined_gds_readback']
    assert physical['net_count']==len(graph['connections'])and physical['instance_count']==len(graph['instances'])
    # Bind every actual geometry input/output, including GDS, ODB and the
    # typed native contact inventory. No independently built leaf can stand
    # in for a different instance scene or different upper-net connectivity.
    for p,digest in physical['inputs'].items():bind(p,digest)
    for name,digest in physical['outputs'].items():bind(geometry/name,digest)
    for p in (manifest_path,graph_path):assert physical['inputs'][str(p)]==candidate['inputs'][str(p)]
    readback=json.loads((geometry/'joined-readback.json').read_text())
    assert readback['passed']and all(readback['checks'].values())and all(readback['native_masks_xor_zero'].values())
    assert readback['physical_instances']==len(graph['instances'])
    assert readback['supply_terminal_counts']=={'net_PG_'+s:len(graph['instances'])+1 for s in ('VDD','VSS')}
    actual={}
    for line in (geometry/'actual-typed-pg.tsv').read_text().splitlines():
        supply,kind,instances,external=line.split('\t');assert supply not in actual
        actual[supply]=dict(type=kind,instances=int(instances),external=int(external))
    assert actual=={s:dict(type=k,instances=len(graph['instances']),external=1)for s,k in [('VDD','POWER'),('VSS','GROUND')]}
    request=json.loads((geometry/'join-input.json').read_text());assert set(request['native'])==set(graph['instances'])
    access_path=Path(graph['pg_access']);bind(access_path,graph['pg_access_sha256']);access=json.loads(access_path.read_text())
    assert access['passed']and not access['candidate_access']
    for p,digest in access['inputs'].items():bind(p,digest)
    native={}
    for top,row in manifest['leaves'].items():
        selected=row['fixed_pg_delivery']
        for field,key in [('path','sha256'),('receipt','receipt_sha256')]:bind(selected[field],selected[key])
        delivery=json.loads(Path(selected['path']).read_text());receipt=json.loads(Path(selected['receipt']).read_text())
        assert receipt['passed']and receipt['native_leaf_qualified']and receipt['outputs']['delivery.json']==selected['sha256']
        assert delivery['passed']and delivery['native_leaf_accepted']and delivery['top']==top and delivery['final_files']==row['final_files']
        assert delivery['signal_pin_plan_unchanged']and delivery['reused_function_and_strict_lec_via_exact_full_view_identity']
        bind(delivery['fixed_pg_receipt'],delivery['fixed_pg_receipt_sha256'])
        assert Path(delivery['fixed_pg_receipt']).resolve()==(Path(access['wrappers'][top]['folder'])/'receipt.json').resolve()
        for field in ('fresh_physical_receipt','fresh_timing_receipt'):bind(delivery[field],delivery[field+'_sha256'])
        pg=json.loads(Path(delivery['fresh_physical_receipt']).read_text());timing=json.loads(Path(delivery['fresh_timing_receipt']).read_text())
        assert pg['passed']and pg['native_pg_connected']and timing['passed']and timing['fresh_native_extraction']and timing['timing_passed']
        for entry in delivery['final_files'].values():bind(entry['path'],entry['sha256'])
        native[top]=dict(delivery=selected,actual_pg_connected=True,instances=sum(t==top for t in graph['instances'].values()))
    for name,top in graph['instances'].items():assert request['native'][name]['sha256']==manifest['leaves'][top]['final_files']['6_final.gds']['sha256']
    negatives={}
    for case in ('missing_native_sink','wrong_supply_pin'):
        broken=copy.deepcopy(graph)
        if case=='missing_native_sink':broken['connections']['PG_VDD']['sinks'].pop()
        else:broken['connections']['PG_VSS']['sinks'][0]['pin']='VDD'
        try:supply_graph(broken)
        except AssertionError:negatives[case]=True
        else:raise AssertionError('Supply-graph negative control accepted: '+case)
    return dict(passed=True,system_pg_qualified=True,whole_system_qualified=False,
        physical_instances=len(graph['instances']),native_types=len(native),native=native,
        actual_typed_supplies=actual,actual_gds_supply_terminal_counts=readback['supply_terminal_counts'],
        negative_controls=negatives,all_native_masks_xor_zero=True,
        scope='Complete actual supply continuity: every qualified native M1-M10 PG path, exact actual native scene, typed ODB supply ports and independently reconstructed upper GDS trees. Signal timing/function/electrical limits still require separate complete system gates; no EM/IR or manufacturing calibration claim.')
