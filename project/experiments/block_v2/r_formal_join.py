"""Require actual successful native producer, simulation and full R proof."""
import json
from pathlib import Path
import shutil
from io_slots import file_sha as sha


def join(root,folder,out,run,function,computation):
    from qualify import source,LIB
    from native_formal import inspect,fixture
    from native_projection_control import verify as projection
    folder,receipt,flow,results=source(folder)
    assert flow['top']=='block_v1_r' and flow['completed_final_native_admission']['passed']
    assert computation is not None and function is not None
    cr=json.loads((computation/'receipt.json').read_text())
    assert cr['passed'] and cr['operation']=='formal-compute'
    f=computation/'formal-computation.json';assert sha(f)==cr['outputs'][f.name]
    computed=json.loads(f.read_text())
    assert computed['passed'] and computed['computation_only'] and computed['top']==flow['top']
    assert not computed['qualified'] and not computed['native_leaf_accepted']
    original=Path(computed['source_snapshot'])
    assert 'issue143-seven-block-v2-20261030' in original.parts and original.parent.name=='snapshots'
    assert sha(original/'source-manifest.json')==computed['source_manifest_sha256']
    manifest=json.loads((original/'source-manifest.json').read_text())
    for name,row in manifest['files'].items():assert sha(original/name)==row['sha256']
    for name,digest in cr['inputs'].items():assert sha(original/name)==digest
    for name,digest in cr['outputs'].items():assert sha(computation/name)==digest
    assert len(cr['commands'])>=5
    assert all(c['returncode']==0 and sha(computation/c['log'])==c['sha256'] for c in cr['commands'])
    for name in ('native_formal.py','native_logic_projection.py','native_tie_projection.py','native_projection_control.py','native_cell_gate.py','structural_view.py'):
        path=Path('project/experiments/block_v1')/name;assert sha(original/path)==sha(root/path)
    raw=Path(flow['raw_source']);captured=computed['stable_final_source']
    assert captured['passed'] and Path(captured['raw_source'])==raw and captured['rtl_sha256']==flow['rtl_sha256']
    actual_raw=json.loads((raw/'receipt.json').read_text());assert actual_raw['passed']
    for name,row in captured['fixed_files'].items():assert sha(raw/name)==row['sha256']==actual_raw['outputs'][name]
    binary=Path('/OpenROAD-flow-scripts/tools/install/kepler-formal/bin/kepler-formal')
    assert cr['commands'][-1]['command']==[str(binary),'--config',str(computation/'kepler.yml')]
    assert computed['binary_sha256']==sha(binary) and computed['library_sha256']==sha(LIB)
    native=inspect((computation/'kepler.log').read_text())
    assert native==computed['strict_native_lec'] and native['passed'] and all(native['checks'].values())
    assert computed['log_sha256']==sha(computation/'kepler.log')
    before=computed['before'];after=computed['after']
    for label,p in [('before',before),('after',after)]:
        assert p==json.loads((computation/(label+'-logic-proof.json')).read_text())
        assert p['passed'] and p['exact_inverse_reconstruction'] and p['emitted_structural_proof']['passed'] and p['used_model_audit']['passed']
        assert p['liberty_sha256']==sha(LIB) and p['logic_netlist_sha256']==sha(computation/(label+'-logic.v'))
        assert p['projected_graph_sha256']==p['constant_functions']['original_graph_sha256']
        assert p['constant_functions']['passed'] and p['constant_functions']['exact_inverse_reconstruction']
    assert before['removed_count']==0 and after['removed_count']>0
    assert before['full_netlist_sha256']==sha(results/'1_synth_lec.v')==computed['synthesis_netlist_sha256']
    fr=json.loads((function/'receipt.json').read_text());assert fr['passed']
    fn=json.loads((function/'final-function.json').read_text())
    assert sha(function/'final-function.json')==fr['outputs']['final-function.json']
    assert fn['passed'] and fn['source_receipt_sha256']==sha(folder/'receipt.json')
    assert len(fn['initial_runs'])==3 and all(r['result']['passed'] for r in fn['initial_runs'].values())
    assert sha(function/'physical-functional.v')==computed['physical_view_sha256']==after['full_netlist_sha256']
    assert sha(function/'original-physical-functional-proof.json')==computed['function_view_sha256']
    control=out/'controls';control.mkdir();(control/'lec').mkdir();fixture(root,control/'lec',run)
    for polarity in (0,1):
        p=control/str(polarity);p.mkdir();projection(root,p,1,lambda cmd,log:run(cmd,'control-'+str(polarity)+'-'+log),polarity)
    current=json.loads((control/'lec/native-formal-control.json').read_text())
    prior=json.loads((computation/'controls/lec/native-formal-control.json').read_text())
    assert current['passed'] and prior['passed'] and current['binary_sha256']==prior['binary_sha256']==sha(binary)
    for name in ('kepler.log','formal.log','before-logic-proof.json','after-logic-proof.json','formal-computation.json'):
        shutil.copyfile(computation/name,out/name)
    shutil.copyfile(computation/'receipt.json',out/'computation-receipt.json')
    result=dict(passed=True,top=flow['top'],strict_native_lec=native,before=before,after=after,
                source_receipt_sha256=sha(folder/'receipt.json'),function_receipt_sha256=sha(function/'receipt.json'),
                computation_receipt_sha256=sha(computation/'receipt.json'),log_sha256=sha(out/'kepler.log'),binary_sha256=sha(binary),
                qualified_hard_macro=False,scope='Actual strict all-boundary final139 computation joined to passed native source and successful same-view final simulations; fresh real controls, all original files rehashed')
    (out/'formal.json').write_text(json.dumps(result,indent=2)+'\n');source(folder)
