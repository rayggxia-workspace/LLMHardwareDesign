"""Static WBS/dependency/scope checks, not protocol/RTL/liveness proof."""
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
    source = args.directory / 'island-sync-plan.json'
    d = json.loads(source.read_text(encoding='utf-8'))
    checks = []

    def check(name, result):
        if not result:
            raise AssertionError(name)
        checks.append(name)

    work = d['work_packages']
    by_id = {w['id']: w for w in work}
    check('12_unique_packages', len(by_id) == len(work) == 12 and set(by_id) == {'W' + str(i) for i in range(12)})
    check('all_proposed', all(w['status'] == 'proposed_not_executed' for w in work))
    check('nonempty_outputs_tests_scope', all(w['outputs'] and w['exit_tests'] and w['acceptance_scope'] for w in work))
    check('relative_not_calendar', all(w['effort'] in ('M', 'L', 'XL') for w in work) and not d['workload_estimate_scale']['calendar_days_or_hours_estimated'])
    check('P1_P7_covered', {p for w in work for p in w['phase_map']} == {'P' + str(i) for i in range(1, 8)})
    visited, active = set(), set()

    def visit(name):
        if name in active:
            raise AssertionError('dependency_cycle:' + name)
        if name in visited:
            return
        active.add(name)
        for dep in by_id[name]['depends_on']:
            if dep not in by_id:
                raise AssertionError('unknown_dependency:' + dep)
            visit(dep)
        active.remove(name)
        visited.add(name)

    for name in by_id:
        visit(name)
    check('dependency_DAG', len(visited) == 12)
    check('EG_N_parallel_after_shell', by_id['W3']['depends_on'] == by_id['W4']['depends_on'] == ['W1'])
    check('full_F_A_after_N_and_EG', 'W3' in by_id['W5']['depends_on'] and 'W4' in by_id['W5']['depends_on'])
    check('MEM_not_after_R_MoE', 'W8' not in by_id['W10']['depends_on'] and 'W9' not in by_id['W10']['depends_on'] and 'W2' in by_id['W10']['depends_on'])
    check('MoE_not_after_R', 'W8' not in by_id['W9']['depends_on'] and by_id['W9']['does_not_require_R_qualification'])
    check('seven_native_obligations', {x['macro'] for x in d['native_sync_obligations']} == set('MNEGRST'))
    check('P2_evidence_not_new_execution', d['P2_existing_evidence']['helper_CASE_PASS'] + d['P2_existing_evidence']['MST_CASE_PASS'] == 19 and not d['new_RTL_implemented'] and not d['new_RTL_SystemC_server_or_EDA_run'])
    check('MST_ACK_counts', d['P2_existing_evidence']['per_normal_batch']['ordinary_S_requests'] == d['P2_existing_evidence']['per_normal_batch']['ordinary_S_ACKs'] == 16)
    check('fragment_not_job_end', not d['cross_island_semantics']['fragment_last_is_whole_job_done'])
    check('maxH_capacity_arithmetic', d['unchanged_limits']['single_token_H_S16_bytes'] == d['unchanged_limits']['max_sample_H'] * 2 == 6144 and d['unchanged_limits']['single_token_H_S32_bytes'] == d['unchanged_limits']['max_sample_H'] * 4 == 12288)
    check('no_M11_active_or_bootload', not d['unchanged_limits']['MEM_NUM_CPU_created_by_M11'] and not d['controller_boundary']['new_program_bootload_allowed'])
    check('no_global_atomicity_or_DAG_proof', not d['unchanged_limits']['whole_token_R_T_MEM_atomicity'] and not d['cross_island_semantics']['DAG_is_physical_deadlock_proof'])
    check('full_source_refs', len(d['input_commit']) == len(d['leaf_source_commit']) == 40)
    result = {
        'status': 'PASS_STATIC_WBS_AND_SCOPE_ONLY',
        'utc_time': datetime.utcnow().isoformat() + 'Z',
        'input_commit': d['input_commit'],
        'leaf_source_commit': d['leaf_source_commit'],
        'tool': sys.version,
        'script_sha256': sha(Path(__file__)),
        'plan_sha256': sha(source),
        'report_sha256': sha(args.report or (args.directory / 'island-sync-plan.md')),
        'checks': checks,
        'new_RTL_model_server_EDA_execution': False,
        'not_proved': ['route RTL', 'numeric correctness', 'live buffer/phase implementation', 'MEM bandwidth/drain', 'deadlock freedom', 'program capacity', 'same-base PPA'],
    }
    if args.receipt:
        args.receipt.write_bytes((json.dumps(result, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))
    print('PASS: {} static WBS checks; no RTL/deadlock/PPA proof'.format(len(checks)))


if __name__ == '__main__':
    main()
