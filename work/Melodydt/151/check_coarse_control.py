"""Research JSON arithmetic/invariant checks; not an RTL or liveness test."""
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
    source = args.directory / 'coarse-control-candidate.json'
    d = json.loads(source.read_text(encoding='utf-8'))
    e = d['candidate_encoding_not_frozen_ABI']
    b = d['transport_storage_budget_example_not_total']
    checks = []

    def check(name, result):
        if not result:
            raise AssertionError(name)
        checks.append(name)

    check('header64', sum(x[1] for x in e['command_header_fields_LSB_first']) == 64)
    check('dynamic_arg64', sum(x[1] for x in e['primary_arg0_fields_LSB_first']) == 64)
    check('event128', sum(x[1] for x in e['event_record_fields_LSB_first']) == 128)
    v = e['data_port_example']
    check('data136', sum(v[x] for x in ['payload_bits', 'valid_bits', 'ready_bits', 'fragment_last_bits', 'valid_bytes_bits']) == 136)
    check('primary16B', 8 * (1 + e['primary_arg_words_max']) == e['primary_RUN_capture_bytes'] == 16)
    x = e['optional_address_extension']
    check('disabled_extension40B', not x['enabled'] and 8 * (1 + x['arg_words_max']) == x['RUN_capture_bytes_if_enabled'] == 40)
    names = ['per_island_primary_RUN_capture_bytes', 'per_island_no_arg_mailbox_bytes', 'per_island_event_hold_bytes', 'per_island_input_hold_bytes', 'per_island_output_hold_bytes']
    check('per_island_partial72B', sum(b[n] for n in names) == b['per_island_subtotal_bytes'] == 72)
    check('four_island_partial352B', 4 * (72 + b['mother_capture_bytes_per_island']) == b['four_island_partial_subtotal_bytes'] == 352)
    check('extension_partial448B', 352 + 4 * b['optional_address_extension_extra_bytes_per_island'] == b['four_island_partial_subtotal_if_address_extension_bytes'] == 448)
    check('five_profiles', set(d['functional_profiles']) == set('AFDHX'))
    check('not_instance_count', d['scope']['finite_profiles_are_not_physical_instance_count'])
    check('not_new_RTL_or_system_pass', not d['implemented_by_this_delivery'] and not d['coarse_system_verified'] and not d['physical_qualified'])
    check('fragment_not_job_end', not v['fragment_last_is_whole_sublayer_done'])
    s = d['finite_storage_boundaries']
    check('H_output_bytes', s['one_token_H_S16_bytes'] == s['eight_sample_max_H'] * 2 == 6144 and s['one_token_H_S32_bytes'] == s['eight_sample_max_H'] * 4 == 12288)
    check('root_bytes_not_payload', d['R_and_state_versions']['metadata_comparison']['runtime_total_at32roots'] == 32 * 32)
    check('no_joint_atomicity', not d['R_and_state_versions']['R_T_cross_island_MEM_global_atomicity'])
    check('risks_unique', len({r['id'] for r in d['risks_and_exit_gates']}) == len(d['risks_and_exit_gates']) == 8)
    result = {
        'status': 'PASS_STATIC_RESEARCH_CHECKS_ONLY',
        'utc_time': datetime.utcnow().isoformat() + 'Z',
        'input_research_ref': d['input_research_ref'],
        'leaf_source_commit': d['leaf_source_commit'],
        'tool': sys.version,
        'script_sha256': sha(Path(__file__)),
        'contract_sha256': sha(source),
        'report_sha256': sha(args.report or (args.directory / 'coarse-control-report.md')),
        'checks': checks,
        'new_RTL_SystemC_EDA_or_model_execution': False,
        'not_proved': ['complete profile program', 'MEM/physical mapping', 'numeric quality', 'drain/deadlock/liveness', 'shared M1-M10 product freeze'],
    }
    if args.receipt:
        args.receipt.write_bytes((json.dumps(result, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))
    print('PASS: {} static research checks; no RTL/liveness/physical proof'.format(len(checks)))


if __name__ == '__main__':
    main()
