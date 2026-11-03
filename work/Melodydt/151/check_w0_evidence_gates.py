"""W0 static traceability and dot8 oracle checks; never invokes RTL tools."""
import argparse
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--directory', type=Path, default=Path(__file__).resolve().parent)
    ap.add_argument('--root', type=Path)
    ap.add_argument('--report', type=Path)
    ap.add_argument('--receipt', type=Path)
    a = ap.parse_args()
    p = a.directory / 'w0-evidence-gates.json'
    d = json.loads(p.read_text(encoding='utf-8'))
    checks = []

    def ck(name, value):
        if not value:
            raise AssertionError(name)
        checks.append(name)

    trace = d['all_P1_requirement_trace']; gates = d['P2_remaining_gates']
    ck('33_unique_requirements', len(trace) == len({x['id'] for x in trace}) == 33)
    ck('13_open_P2_gates', {x['id'] for x in gates} == {x['id'] for x in trace if x['original_phase'] == 'P2'} and len(gates) == 13 and all(x['gate_status'] == 'OPEN_NOT_EXECUTED' for x in gates))
    cases = d['actual_P2']['cases']; case_ids = {x['id'] for x in cases}
    ck('19_historical_cases', len(cases) == len(case_ids) == d['actual_P2']['case_count'] == 19)
    ck('all_case_refs_real', all(set(x['actual_case_ids']) <= case_ids for x in trace))
    tests = [t for g in gates for t in g['remaining_tests']]
    ck('20_unique_future_tests', len(tests) == len({t['test_name'] for t in tests}) == 20)
    ck('future_tests_unexecuted_and_decidable', all(t['execution_status'] == 'NOT_EXECUTED_FUTURE_REQUIREMENT' and t['planned_inputs'] and t['decidable_expected'] and t['required_evidence_layer'] for t in tests))
    ck('future_W_names_valid', all(w in {'W'+str(i) for i in range(12)} for t in tests for w in t['future_work_packages']))
    ck('no_P2_acceptance', not d['actual_P2']['P2_fully_accepted'] and not d['completion_claims']['P2_fully_accepted'])
    ck('W0_prepared_not_accepted', d['completion_claims']['W0_artifacts_prepared'] and not d['completion_claims']['W0_independently_accepted'] and len(d['W0_exit_checklist']) == 8)
    ck('no_new_implementation', not d['this_delivery_new_RTL_or_simulation'] and not d['completion_claims']['W1_implemented'] and not d['completion_claims']['full_profiles_implemented'])
    w = d['W1_minimal_contract']; i = w['ingress']; c = w['counts']
    ck('fixed_W1_not_bootload_or_config', not w['program_loading'] and not w['runtime_shape_address_opcode_scale_configuration'])
    ck('input_payload_padding_math', i['ordered_beats'] * i['beat_bits'] // 8 == i['transfer_bytes'] == 128 and i['effective_A_bytes'] + i['effective_B_bytes'] == i['effective_payload_bytes'] == 72 and 128-72 == i['padding_written_zero_bytes'] == 56)
    ck('frame_RUN_vs_RUN_counts', c['ingress_phase_S_writes_ACKs'] == 8 and c['RUN_S_result_writes_ACKs'] + c['RUN_S_reads_ACKs'] == c['RUN_S_transactions'] == 8 and c['frame_plus_RUN_S_transactions'] == 16)
    ck('old_ABI_disposition_explicit', len(d['design_dispositions_pending_review']) == 2 and not d['design_dispositions_pending_review'][0]['W1_min_requires_old_representation'] and not d['design_dispositions_pending_review'][1]['W1_min_requires_generic_tags'])
    vectors = w['oracle']['future_vectors']
    ck('five_future_vectors', len(vectors) == len({v['id'] for v in vectors}) == 5)
    for v in vectors:
        r = [sum(v['A'][k] * v['B_columns'][n][k] for k in range(8)) for n in range(8)]
        ck(v['id']+'_dot8', r == v['expected_S64'] and all(-130048 <= x <= 131072 for x in r))
        expected = ['%032x'%((r[n] & ((1<<64)-1)) | ((r[n+1] & ((1<<64)-1)) << 64)) for n in range(0,8,2)]
        ck(v['id']+'_pair_order', expected == v['expected_output128_hex'])
        raw = [int(x,16) for x in v['ingress_words_hex']]
        ck(v['id']+'_A_padding', len(raw) == 8 and raw[0] >> 64 == 0 and raw[1:4] == [0,0,0])
        A = [(raw[0] >> (8*k)) & 255 for k in range(8)]
        A = [x-256 if x >= 128 else x for x in A]
        Bword = sum(raw[4+j] << (128*j) for j in range(4))
        B = [[(Bword >> (8*(8*n+k))) & 255 for k in range(8)] for n in range(8)]
        B = [[x-256 if x>=128 else x for x in row] for row in B]
        ck(v['id']+'_ingress_order', A == v['A'] and B == v['B_columns'] and v['RTL_execution_status'] == 'NOT_EXECUTED_W1_FUTURE_VECTOR')
    ck('positive_negative_extremes', vectors[2]['expected_S64'] == [131072]*8 and vectors[3]['expected_S64'] == [-130048]*8)
    ck('six_W1_future_checks', len(w['required_future_tests']) == 6)
    ck('full_refs', len(d['input_parent_full_commit']) == len(d['leaf_source_commit']) == 40)
    ck('historical_six_exit0', len(d['actual_P2']['run_exit_codes']) == 6 and all(x['exit_code'] == 0 for x in d['actual_P2']['run_exit_codes']))
    if a.root:
        for item in d['source_index']:
            ck('source_'+item['path'], sha(a.root/item['path']) == item['sha256'])
    receipt = {'status':'PASS_STATIC_W0_TRACE_AND_ORACLE_ONLY','utc_time':datetime.utcnow().isoformat()+'Z','input_parent_full_commit':d['input_parent_full_commit'],'leaf_source_commit':d['leaf_source_commit'],'python':sys.version,'script_sha256':sha(Path(__file__)),'gates_sha256':sha(p),'report_sha256':sha(a.report or a.directory/'w0-evidence-gates.md'),'checks':checks,'new_RTL_SystemC_server_EDA':False,'source_index_checked':bool(a.root),'not_proved':['W0 independent acceptance','P2 full phase','W1 RTL','full profiles','numeric model quality','liveness','physical qualification']}
    if a.receipt:
        a.receipt.write_bytes((json.dumps(receipt,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
    print('PASS: {} static W0 checks;19 historical cases/13 open gates/20 future tests/5 future vectors; no new RTL'.format(len(checks)))


if __name__ == '__main__':
    main()
