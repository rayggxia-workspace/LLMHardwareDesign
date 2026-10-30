"""Source-bound physical prerequisites for the repaired mixed simulation."""
import copy
import json
from pathlib import Path
from native_views import received_contract


def contract(physical,formal,source,receipt_sha256,pipeline,top,policy,netlist_sha256):
    received_contract(physical,source,receipt_sha256,pipeline,top,policy)
    assert formal==physical['mapped_to_final_lec'],'Mixed formal proof is not the accepted physical proof'
    assert formal['passed'] is True and all(v is True for v in formal['checks'].values())
    assert formal['full_final_netlist_sha256']==netlist_sha256
    view=formal['physical_functional_view'];assert view['passed'] is True
    assert view['full_view'] and view['full_view_sha256']
    results=source/'flow/results/nangate45'/('bv1_'+top+'_'+policy)/'base'
    assert view['input_sha256'][str(results/'6_final.v')]==netlist_sha256
    assert str(results/'6_final.odb') in view['input_sha256']
    return dict(passed=True,top=top,policy=policy,pipeline=pipeline,
        source=str(source),source_receipt_sha256=receipt_sha256,
        full_final_netlist_sha256=netlist_sha256,full_view_sha256=view['full_view_sha256'])


def receive(record):
    """Called again by the mathematical receiver before accepting results."""
    from io_slots import file_sha
    expected=dict(shared109='native_pipeline_c8_escape.json',transaction6k='native_pipeline_escape.json')
    assert record['physical_contract_required'] is True and set(record['physical_receivers'])==set(expected)
    results={}
    for top,pipeline in expected.items():
        entry=record['physical_receivers'][top];leaf=record['leaves'][top]
        assert entry['pipeline']==leaf['pipeline']==pipeline
        report=Path(entry['report']);receipt=Path(entry['receipt'])
        assert report.parent==receipt.parent and receipt.name=='receipt.json'
        assert record['inputs'][str(receipt)]==entry['receipt_sha256']==file_sha(receipt)
        assert record['inputs'][str(report)]==entry['report_sha256']==file_sha(report)
        bound=json.loads(receipt.read_text());assert bound['passed'] is True
        assert bound['outputs'][report.name]==entry['report_sha256']
        physical=json.loads(report.read_text());formal=json.loads(Path(leaf['formal']).read_text())
        source=Path(leaf['receipt']).parent
        results[top]=contract(physical,formal,source,record['inputs'][leaf['receipt']],pipeline,top,record['policy'],leaf['original_final_sha256'])
        view=formal['physical_functional_view']
        assert view['input_sha256'][str(source/next(n for n in leaf['sealed_outputs']if n.endswith('/6_final.odb')))]==next(h for n,h in leaf['sealed_outputs'].items()if n.endswith('/6_final.odb'))
        for name in ['physical-functional.v','physical-functional-proof.json']:
            assert file_sha(report.parent/name)==bound['outputs'][name]
        assert str(report.parent/'physical-functional.v')==view['full_view']
        assert file_sha(Path(view['full_view']))==view['full_view_sha256']
        assert json.loads((report.parent/'physical-functional-proof.json').read_text())==view
        for side in ['before','after']:
            assert formal['boolean_projection'][side]['liberty_sha256']==record['inputs'][record['library']]
    return results


def verify(root,out,cpus):
    """Actual accepted T6K controls plus deliberate contract corruptions."""
    from io_slots import file_sha
    assert cpus==1
    base=out.parents[2];reports={};faults={}
    for policy in ['A','C']:
        folder=base/'block-v1-20261027-161/tasks'/('native-escape-receive-transaction6k-'+policy.lower())
        receipt=json.loads((folder/'receipt.json').read_text());assert receipt['passed'] is True
        path=folder/'native-physical-receiver.json';assert file_sha(path)==receipt['outputs'][path.name]
        physical=json.loads(path.read_text());formal=physical['mapped_to_final_lec'];source=Path(physical['source'])
        source_receipt_sha256=physical['source_receipt_sha256'];netlist=formal['full_final_netlist_sha256']
        args=(source,source_receipt_sha256,'native_pipeline_escape.json','transaction6k',policy,netlist)
        assert contract(physical,formal,*args)['passed'] is True
        variants={}
        for name in ['passed','historical_input_contract','source','source_receipt_sha256','pipeline','top','policy','independent_drc_items','rc_coverage_qualified']:
            p=copy.deepcopy(physical)
            p[name]=False if name in ['passed','rc_coverage_qualified']else True if name=='historical_input_contract'else 1 if name=='independent_drc_items'else 'wrong'
            variants[name]=(p,formal,args)
        for name in ['timing','rc_coverage','mapped_to_final_lec','independent_native_drc_zero','exact_prefabricated_m10_pins','all_pg_iterms_correct']:
            p=copy.deepcopy(physical);p['checks'][name]=False;variants['check-'+name]=(p,formal,args)
        p=copy.deepcopy(physical);del p['checks']['mapped_to_final_lec'];variants['missing-formal-check']=(p,formal,args)
        p=copy.deepcopy(physical);f=p['mapped_to_final_lec'];f['full_final_netlist_sha256']='wrong';variants['different-final-netlist']=(p,f,args)
        p=copy.deepcopy(physical);f=p['mapped_to_final_lec'];f['physical_functional_view']['input_sha256'][str(source/'flow/results/nangate45'/('bv1_transaction6k_'+policy)/'base/6_final.v')]='wrong';variants['different-view-input']=(p,f,args)
        p=copy.deepcopy(physical);f=p['mapped_to_final_lec'];f['physical_functional_view']['passed']=False;variants['failed-full-view']=(p,f,args)
        for name,(p,f,arguments) in variants.items():
            try:contract(p,f,*arguments)
            except (AssertionError,KeyError):faults[policy+'-'+name]=True
            else:raise AssertionError('Corrupt physical prerequisite accepted: '+policy+'-'+name)
        reports[policy]=dict(source=str(folder),report_sha256=file_sha(path),receipt_sha256=file_sha(folder/'receipt.json'),positive=True)
    result=dict(schema='block-v1-native-composed-physical-control/1',passed=True,actual=reports,rejected_faults=faults,
        module_sha256=file_sha(Path(__file__)),qualified_hard_macro=False,
        scope='Actual accepted T6K physical/formal/full-view contract and corruptions; C8 source still requires its own complete successful receiver')
    (out/'native-composed-physical-control.json').write_text(json.dumps(result,indent=2)+'\n')
