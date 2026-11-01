"""Receive actual final-R simulation only after its native source is accepted."""
import copy,json
from pathlib import Path
import shutil
from io_slots import file_sha as sha


def join(root,folder,out,computation):
    from qualify import source,LIB
    from retain_r import adapt
    folder,sealed_receipt,flow,results=source(folder)
    assert flow['top']=='block_v1_r' and flow['completed_final_native_admission']['passed']
    assert computation is not None
    cr=json.loads((computation/'receipt.json').read_text())
    assert cr['passed'] and cr['operation']=='function-compute'
    f=computation/'function-computation.json'
    assert sha(f)==cr['outputs'][f.name]
    computed=json.loads(f.read_text())
    assert computed['passed'] and computed['computation_only']
    assert not computed['qualified'] and not computed['native_leaf_accepted']
    assert computed['top']==computed['test_top']==flow['top']
    original=Path(computed['source_snapshot'])
    assert 'issue143-seven-block-v2-20261030' in original.parts and original.parent.name=='snapshots'
    assert sha(original/'source-manifest.json')==computed['source_manifest_sha256']
    manifest=json.loads((original/'source-manifest.json').read_text())
    for name,row in manifest['files'].items():assert sha(original/name)==row['sha256']
    for name,digest in cr['inputs'].items():assert sha(original/name)==digest
    for name,digest in cr['outputs'].items():assert sha(computation/name)==digest
    assert all(c['returncode']==0 and sha(computation/c['log'])==c['sha256'] for c in cr['commands'])
    raw=Path(flow['raw_source']);captured=computed['stable_final_source']
    assert captured['passed'] and Path(captured['raw_source'])==raw and captured['rtl_sha256']==flow['rtl_sha256']
    actual_raw=json.loads((raw/'receipt.json').read_text());assert actual_raw['passed']
    for name,row in captured['fixed_files'].items():
        assert sha(raw/name)==row['sha256']==actual_raw['outputs'][name]
    view=computed['full_final_netlist']
    assert view['passed'] and sha(computation/'physical-functional-proof.json')==cr['outputs']['physical-functional-proof.json']
    assert json.loads((computation/'physical-functional-proof.json').read_text())==view
    assert Path(view['full_view'])==computation/'physical-functional.v'
    assert sha(computation/'physical-functional.v')==view['full_view_sha256']
    assert view['input_sha256']=={str(raw/'flow/results/nangate45/bv1_block_v1_r/base'/name):sha(results/name) for name in ('6_final.odb','6_final.v')}
    assert computed['library_sha256']==sha(LIB)
    bench=adapt((root/'project/experiments/block_v1/test_recurrent_macro.cpp').read_text())
    assert (computation/'test-r.cpp').read_text()==bench
    assert computed['bench_sha256']==computed['compiled_bench_sha256']==sha(computation/'test-r.cpp')
    assert computed['cell_models_sha256']==sha(computation/'cells.v')
    runs=computed['initial_runs']
    assert set(runs)=={'all-ones','random-143','random-144'}
    for name,initial,seed in [('all-ones',1,143),('random-143',2,143),('random-144',2,144)]:
        row=runs[name]
        assert row['initial']==initial and row['seed']==seed and row['result']['passed']
        assert row['log_sha256']==sha(computation/(name+'.log'))
        assert json.loads((computation/(name+'.log')).read_text())==row['result']==runs['all-ones']['result']
    for name in ('physical-functional.v','cells.v','test-r.cpp','all-ones.log','random-143.log','random-144.log'):
        shutil.copyfile(computation/name,out/name);assert sha(out/name)==cr['outputs'][name]
    shutil.copyfile(computation/'receipt.json',out/'function-computation-receipt.json')
    shutil.copyfile(f,out/f.name)
    shutil.copyfile(computation/'physical-functional-proof.json',out/'original-physical-functional-proof.json')
    rebound=copy.deepcopy(view)
    rebound.update(full_view=str(out/'physical-functional.v'),
                   input_sha256={str(results/name):sha(results/name) for name in ('6_final.odb','6_final.v')},
                   exact_input_rebind=dict(passed=True,original_proof_sha256=sha(computation/'physical-functional-proof.json'),
                       original_inputs=view['input_sha256'],same_input_bytes=True,
                       scope='Only paths rebound after exact original and sealed ODB/V hash equality; generated physical view byte-identical'))
    (out/'physical-functional-proof.json').write_text(json.dumps(rebound,indent=2)+'\n')
    result=copy.deepcopy(computed)
    result.pop('computation_only');result.pop('qualified');result.pop('native_leaf_accepted')
    result.update(source_receipt_sha256=sha(folder/'receipt.json'),full_final_netlist=rebound,
                  computation_receipt_sha256=sha(computation/'receipt.json'),
                  scope='Actual three-initial-state full final139 physical-netlist simulations received only after passed native producer and exact sealed input identity; all other gates mandatory')
    (out/'final-function.json').write_text(json.dumps(result,indent=2)+'\n')
    source(folder)
