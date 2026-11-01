"""Static count/accounting checks only; no RTL, numerical or physical proof."""
import argparse
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--directory', type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument('--receipt', type=Path)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    source = args.directory / 'block-control-sizing.json'
    d = json.loads(source.read_text(encoding='utf-8'))
    checks = []

    def check(name, result):
        if not result:
            raise AssertionError(name)
        checks.append(name)

    check('MNEGRST_order', d['macro_order'] == ['M', 'N', 'E', 'G', 'R', 'S', 'T'])
    expected = {'A_plain': [1,1,1,0,0,1,1], 'A_gate': [1,1,1,1,0,1,1], 'F': [1,1,1,1,0,1,1], 'X': [1,1,1,1,0,1,1], 'D': [1,1,1,1,1,1,1], 'H': [1,1,1,1,1,1,1]}
    rows = {r['profile']: r for r in d['serial_reference_function_blocks']}
    check('six_profile_rows', set(rows) == set(expected))
    for name in sorted(expected):
        r = rows[name]
        check(name + '_vector_sum_CTRL', r['counts'] == expected[name] and sum(r['counts']) == r['leaf_total'] and r['local_CTRL_domains'] == 1)
    check('global_mother_separate', d['ownership_and_serial_conditions']['global_mother_reference_count_chipwide'] == 1 and not d['ownership_and_serial_conditions']['global_mother_in_per_block_CTRL_count'])
    h = d['H_complete_main_reference']
    check('complete_H_onceNorm7', h['counts'] == expected['H'] and h['leaf_total'] == 7 and h['inputNorm_execution_count'] == 1)
    s = d['H_split_comparison']
    summed = [sum(r['counts'][i] for r in s['wrappers']) for i in range(7)]
    check('split_H12', summed == s['summed_counts'] == [2,2,2,1,1,2,2] and sum(summed) == s['leaf_total'] == 12)
    check('split_H_CTRL2_onceNorm', sum(r['local_CTRL_domains'] for r in s['wrappers']) == s['local_CTRL_domains'] == 2 and s['inputNorm_execution_count'] == 1)
    n = s['optional_separate_NormJoin']
    check('optional_NormJoin16', [summed[i] + n['NormJoin_counts'][i] for i in range(7)] == n['total_counts'] and sum(n['total_counts']) == n['leaf_total'] == 16 and n['CTRL_domains'] == 3)
    x = s['optional_shared_resource_cluster']
    check('optional_cluster8', x['counts'] == [2,1,1,1,1,1,1] and sum(x['counts']) == x['leaf_total'] == 8 and not x['performance_equivalent_to_split'])
    m = h['memory_example']
    check('H_lifetime_example', m['S16_H_vector_bytes'] == m['Falcon_H'] * 2 == 5120 and m['four_vectors_if_simultaneously_retained_bytes'] == len(m['four_vector_names']) * 5120 == 20480 and not m['four_vectors_are_mandatory_lower_bound'])
    check('SSM_vector_not_Tfit', m['SSM4096_S16_vector_bytes'] == 4096 * 2 == 8192 and 8192 > m['native_T_bytes'])
    c = d['classification']['candidate_vector_classes']
    check('state_type_not_DH_locked', set(c[-1]['candidate_profiles']) == set(expected) and not d['classification']['BOM_superset_guarantees_profile_support'])
    check('T_not_lower_bound', d['scope']['T1_is_provisional_batch_spool_interface_choice_not_algorithm_lower_bound'] and not d['scope']['counts_are_minimum_proof'])
    check('no_new_RTL_run_or_remote', not d['new_RTL_implemented'] and not d['simulation_server_or_EDA_executed'] and not d['remote_or_formal_tree_modified'])
    check('same_base_no_short_or_new_MUX', d['fixed_base_constraints']['same_M1_M10_for_every_product'] and not d['fixed_base_constraints']['multiple_push_pull_outputs_can_short_if_valid_exclusive'] and not d['fixed_base_constraints']['custom_layers_can_add_MUX_buffer_CTS'])
    result = {'status': 'PASS_STATIC_RESEARCH_COUNTS_ONLY', 'utc_time': datetime.utcnow().isoformat() + 'Z', 'input_ref': d['input_ref'], 'input_full_commit': d['input_full_commit'], 'leaf_source_commit': d['leaf_source_commit'], 'tool': sys.version, 'script_sha256': sha(Path(__file__)), 'contract_sha256': sha(source), 'report_sha256': sha(args.report or (args.directory / 'block-control-sizing.md')), 'checks': checks, 'RTL_model_server_EDA_executed': False, 'not_proved': ['minimum or optimal macro counts', 'full model mapping/numerics', 'MEM bandwidth/drain', 'throughput equivalence', 'shared-resource liveness', 'same-base physical freeze']}
    if args.receipt:
        args.receipt.write_bytes((json.dumps(result, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))
    print('PASS: {} static sizing checks; no RTL/PPA/throughput proof'.format(len(checks)))


if __name__ == '__main__':
    main()
