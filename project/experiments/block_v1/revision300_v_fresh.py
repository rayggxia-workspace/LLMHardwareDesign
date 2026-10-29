"""Corrected V starts every physical stage again; never reads old CTS data."""
import json


def implement(root,out,cpus,run):
    from revision300_flow import implement as fresh
    from io_slots import file_sha
    import hashlib
    policy=json.loads((root/'project/experiments/block_v1/revision300-v-fresh.json').read_text())
    assert policy==dict(schema='revision300-v-fresh/1',
        mapping='block-v1-20261029-321/tasks/revision300-map-v',
        function='block-v1-20261029-321/tasks/revision300-test-v',
        upper_layer_adjustment=.20,congestion_iterations=100,
        inherited_physical_stages=[],requires_fresh_final_acceptance=True)
    base=out.parents[2]
    proof=base/'block-v1-20261029-304/tasks/revision300-v-carry-proof'
    receipt=json.loads((proof/'receipt.json').read_text())
    assert receipt['passed'] and receipt['mode']=='revision300-v-carry-proof'
    for name in ('revision300-v-carry-proof.json','proof.sv','positive.log','single-bit-negative.log'):
        assert file_sha(proof/name)==receipt['outputs'][name]
    record=json.loads((proof/'revision300-v-carry-proof.json').read_text())
    assert record['passed'] and record['unconstrained_input_bits']==264
    assert record['actual_single_bit_negative_rejected']
    relative='project/rtl/block_library_v1/block_v1_v.sv'
    original=base/'block-v1-20261029-304/src'/relative
    assert file_sha(original)==record['rtl_sha256']==receipt['inputs'][relative]
    functions={}
    for name in ('add128_grouped','rne'):
        extracted=[]
        for path in (original,root/relative):
            text=path.read_text();start=text.index(' function automatic signed [127:0] '+name+';')
            end=text.index(' endfunction',start)+len(' endfunction');extracted.append(text[start:end])
        assert extracted[0]==extracted[1], 'Changed mathematical function requires new proof'
        functions[name]=hashlib.sha256(extracted[1].encode()).hexdigest()
    (out/'carry-proof-reuse.json').write_text(json.dumps(dict(passed=True,
        original_proof_receipt_sha256=file_sha(proof/'receipt.json'),actual_function_sha256=functions,
        current_rtl_sha256=file_sha(root/relative),scope='Only identical combinational functions; full macro checks remain independently required.'),indent=2)+'\n')
    fresh(root,out,cpus,run,'v',prerequisite_tasks={k:policy[k]for k in ('mapping','function')},
          routing_policy={k:policy[k]for k in ('upper_layer_adjustment','congestion_iterations')})
