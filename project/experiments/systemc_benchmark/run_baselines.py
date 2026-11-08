"""Six old220 plan re-evaluations and real SystemC kernel runs on one node."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import subprocess
import sys


def run(args):
    result = subprocess.run([str(x) for x in args], stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, universal_newlines=True)
    if result.returncode:
        raise RuntimeError(result.stderr[-4000:])
    return result.stdout


def main():
    p = argparse.ArgumentParser()
    p.add_argument('old_generated', type=Path)
    p.add_argument('output', type=Path)
    a = p.parse_args()
    a.output.mkdir(exist_ok=False)

    def worker(case):
        name, ir_name, plan_name, greedy = case
        out = a.output / name
        original_plan = a.old_generated / (plan_name + '-plan.json')
        if greedy:
            plan = json.loads(original_plan.read_text())['baseline']
            selected = a.output / (name + '-selected.json')
            selected.write_text(json.dumps(plan) + '\n')
        else:
            selected = original_plan
        stdout = run([sys.executable, 'baseline_trace.py',
                      a.old_generated / (ir_name + '-ir.json'), selected,
                      'frozen-transition.py', out])
        (out / 'builder.log').write_text(stdout)
        stdout = run(['./timed-resources', out / 'trace.tsv'])
        (out / 'systemc.log').write_text(stdout)
        result, = [json.loads(line[7:]) for line in stdout.splitlines() if line.startswith('RESULT ')]
        audit = json.loads((out / 'audit.json').read_text())
        delta = result['makespan_ps'] - audit['expected_makespan_ps_lower']
        if not 0 <= delta < audit['rounding_error_ps_upper_exclusive']:
            raise ValueError('SystemC differs from independent old conservative bound')
        if result['energy_complete']:
            raise ValueError('unknown energy incorrectly qualified')
        return {'case': name, 'systemc_makespan_ps': result['makespan_ps'],
                'core_ticks': audit['recomputed_core_ticks'],
                'external_128bit_words': audit['external_128bit_words'],
                'rounding_difference_ps': delta, 'energy_complete': False,
                'timing_qualified': False, 'decode_qualified': False,
                'scope': audit['scope'], 'inputs': audit['inputs'],
                'trace_sha256': audit['trace_sha256'],
                'systemc_log_sha256': hashlib.sha256(stdout.encode()).hexdigest()}

    cases = []
    for tag, ir, plan in [('five', 'five-groups', 'five-groups'),
                          ('nine', 'nine-groups-count-experiment', 'nine-groups-count-experiment'),
                          ('nine-budget', 'nine-groups-count-experiment', 'nine-groups-budget')]:
        cases.extend([(tag + '-dp', ir, plan, False), (tag + '-greedy', ir, plan, True)])
    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(worker, cases))
    (a.output / 'summary.json').write_text(json.dumps(results, indent=2) + '\n')
    print(json.dumps({'old_kernel_runs': len(results), 'systemc_consistency_passed': True,
                      'qualified_system_timing': False, 'qualified_energy': False}))


if __name__ == '__main__':
    main()
