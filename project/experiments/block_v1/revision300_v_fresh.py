"""Corrected V starts every physical stage again; never reads old CTS data."""
import json


def implement(root,out,cpus,run):
    from revision300_flow import implement as fresh
    from io_slots import file_sha
    import hashlib
    policy=json.loads((root/'project/experiments/block_v1/revision300-v-fresh.json').read_text())
    assert policy==dict(schema='revision300-v-fresh/1',
        mapping='block-v1-20261030-576/tasks/revision300-map-v',
        function='block-v1-20261030-576/tasks/revision300-test-v',
        normalization_arithmetic_proof='block-v1-20261030-576/tasks/revision300-v-norm-proof',
        group_arithmetic_proof='block-v1-20261029-348/tasks/revision300-v-group-proof',
        upper_layer_adjustment=.20,congestion_iterations=100,clock_ndr='none',
        hold_slack_margin_ns=.080,inherited_physical_stages=[],requires_fresh_final_acceptance=True)
    base=out.parents[2]
    norm_proof=base/policy['normalization_arithmetic_proof']
    norm_receipt=json.loads((norm_proof/'receipt.json').read_text())
    assert norm_receipt['passed'] and norm_receipt['mode']=='revision300-v-norm-proof'
    for name in ('revision300-v-norm-proof.json','proof.sv','positive.log','single-bit-negative.log'):
        assert file_sha(norm_proof/name)==norm_receipt['outputs'][name]
    norm_record=json.loads((norm_proof/'revision300-v-norm-proof.json').read_text())
    assert norm_record['passed'] and norm_record['unconstrained_input_bits']==130
    assert norm_record['full128bit_signed_merge_rne32_equivalent'] and norm_record['actual_single_bit_negative_rejected']
    norm_relative='project/rtl/block_library_v1/block_v1_v.sv'
    assert file_sha(root/norm_relative)==norm_record['rtl_sha256']==norm_receipt['inputs'][norm_relative]
    (out/'norm-proof-reuse.json').write_text(json.dumps(dict(passed=True,
        original_proof_receipt_sha256=file_sha(norm_proof/'receipt.json'),
        current_rtl_sha256=file_sha(root/norm_relative),
        scope='All-input exact normalization identity only; fresh final physical gates remain required.'),indent=2)+'\n')
    point_proof=base/'block-v1-20261030-576/tasks/revision300-v-carry-proof'
    point_receipt=json.loads((point_proof/'receipt.json').read_text())
    assert point_receipt['passed'] and point_receipt['mode']=='revision300-v-carry-proof'
    for name in ('revision300-v-carry-proof.json','proof.sv','positive.log','single-bit-negative.log','half-carry-negative.log'):
        assert file_sha(point_proof/name)==point_receipt['outputs'][name]
    point_record=json.loads((point_proof/'revision300-v-carry-proof.json').read_text())
    assert point_record['passed'] and point_record['unconstrained_input_bits']==264
    assert point_record['point_registered_quotient_and_increment_full128bit_equivalent']
    assert point_record['point_two_half_increment_and_registered_carry_full128bit_equivalent']
    assert point_record['corrupted_half_carry_negative_rejected']
    assert point_record['normalization_denominator_prefix_full128bit_equivalent']
    assert point_record['actual_single_bit_negative_rejected']
    assert file_sha(root/norm_relative)==point_record['rtl_sha256']==point_receipt['inputs'][norm_relative]
    (out/'point-round-proof-reuse.json').write_text(json.dumps(dict(passed=True,
        original_proof_receipt_sha256=file_sha(point_proof/'receipt.json'),
        current_rtl_sha256=file_sha(root/norm_relative),
        scope='All-input full128bit point quotient/two-half increment and registered carry identity; final gates remain required.'),indent=2)+'\n')
    group_proof=base/policy['group_arithmetic_proof']
    group_receipt=json.loads((group_proof/'receipt.json').read_text())
    assert group_receipt['passed'] and group_receipt['mode']=='revision300-v-group-proof'
    for name in ('revision300-v-group-proof.json','proof.sv','positive.log','single-bit-negative.log'):
        assert file_sha(group_proof/name)==group_receipt['outputs'][name]
    group_record=json.loads((group_proof/'revision300-v-group-proof.json').read_text())
    assert group_record['passed'] and group_record['unconstrained_input_bits']==260
    assert group_record['full130bit_difference_and_no_borrow_and_selection_equivalent']
    assert group_record['actual_single_bit_negative_rejected']
    group_relative='project/rtl/block_library_v1/block_v1_v_group.sv'
    assert file_sha(root/group_relative)==group_record['rtl_sha256']==group_receipt['inputs'][group_relative]
    (out/'group-proof-reuse.json').write_text(json.dumps(dict(passed=True,
        original_proof_receipt_sha256=file_sha(group_proof/'receipt.json'),
        current_group_rtl_sha256=file_sha(root/group_relative),
        scope='Only all-input combinational arithmetic identity; complete new-source physical and final gates remain required.'),indent=2)+'\n')
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
          routing_policy={k:policy[k]for k in ('upper_layer_adjustment','congestion_iterations','clock_ndr')},
          timing_policy=dict(hold_slack_margin_ns=policy['hold_slack_margin_ns']))
