"""Execute the actual C++ candidate on small traces and malformed arguments.

Place beside study_audit.py. Intended for the task's Slurm allocation only.
run_edges(model, out) creates a fresh out/edge-cases directory and returns its
JSON-serializable receipt; it never rewrites a previous run.
"""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess

import study_audit


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def make_trace(n, k, bits):
    # One S32 row and a packed static weight matrix, both initially in backing.
    # No additional operators can hide empty-P or tail behavior in this test.
    return (f'3 1 1\n0 {k} 32 1\n1 {n*k} {bits} 1\n2 {n} 32 0\n'
            f'2 Dot {n} 1 {n} {k} 1 0 0 2 0 1\n')


def invoke(model, trace, profile, variant, extra, log, cwd, expected_error=False):
    command = [str(model), str(trace), profile, variant, *map(str, extra)]
    process = subprocess.run(command, cwd=cwd, stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT)
    log.write_bytes(process.stdout)
    text = process.stdout.decode('utf-8', errors='replace')
    receipt = dict(command=command, returncode=process.returncode,
                   log=log.name, log_sha256=digest(log))
    if expected_error:
        check(process.returncode != 0, 'invalid argument was accepted: '+str(extra))
        check('invalid context' in text, 'missing explicit context error: '+text[-1000:])
        check(not any(line.startswith('RESULT ') for line in text.splitlines()),
              'invalid argument produced a successful result')
        return None, receipt
    check(process.returncode == 0, 'candidate failed: '+str(command)+'\n'+text[-3000:])
    check('MODEL_FAILURE' not in text, 'candidate emitted MODEL_FAILURE')
    check('SystemC 3.0.2' in text, 'unexpected SystemC version/banner')
    results = [json.loads(line[7:]) for line in text.splitlines() if line.startswith('RESULT ')]
    check(len(results) == 1, 'missing/ambiguous candidate result')
    return results[0], receipt


def run_edges(model: Path, out: Path):
    model, out = Path(model).resolve(), Path(out).resolve()
    check(model.is_file(), 'missing model executable')
    out.mkdir(parents=True, exist_ok=True)
    work = out/'edge-cases'
    work.mkdir(exist_ok=False)
    best = 'adaptive_prefix_pair_combine'
    shapes = [(1, 4097, 8, 'observe'),
              (9, 4353, 8, best),
              (17, 11009, 16, 'observe'),
              (129, 4097, 8, best),
              (129, 4353, 16, best)]
    cases = [(n, k, bits, variant, contexts, 1, reuse)
             for n, k, bits, variant in shapes
             for contexts, reuse in ((1, 1), (2, 1), (8, 1), (16, 0))]
    # With two P workers, N129 only has at most nine N8 blocks per worker.
    # N257 additionally exercises sixteen occupied contexts and their next group.
    cases.append((257, 4353, 8, 'observe', 16, 1, 1))
    baselines, traces, baseline_receipts, records = {}, {}, [], []
    coverage = dict(empty_worker=False, tail_N=False, tail_K=False,
                    full_16_contexts=False, group_reuse=False,
                    explicit_context1_regression=False, reuse_disabled=False)

    for n, k, bits, variant, contexts, switch, reuse in cases:
        profile = f'queued_pipe_w{bits}'
        key = (n, k, bits, variant)
        prefix = f'n{n}-k{k}-w{bits}-{variant}'
        if key not in baselines:
            trace = work/(prefix+'.trace')
            trace.write_bytes(make_trace(n, k, bits).encode())
            traces[key] = trace
            # Default CLI chooses contexts=1. Strip only the added study field
            # to obtain the frozen-path shape baseline used by the audit.
            base, receipt = invoke(model, trace, profile, variant, [],
                                   work/(prefix+'-default.log'), work)
            baseline = deepcopy(base)
            study = baseline.pop('context_study')
            check(study['contexts'] == 1 and study['switch_cycles'] == 0 and study['reuse_A'],
                  'unexpected default context configuration')
            for actor in study['P']:
                check(actor['enabled_calls'] == 0, 'default CLI entered candidate worker')
            study_audit.legacy.check(baseline, trace)
            baselines[key] = baseline
            receipt.update(N=n, K=k, bits=bits, profile=profile, variant=variant,
                           trace=trace.name, trace_sha256=digest(trace), result=base)
            baseline_receipts.append(receipt)
            (work/(prefix+'-default.json')).write_text(json.dumps(receipt, indent=2)+'\n',
                                                     encoding='utf-8')

        trace, baseline = traces[key], baselines[key]
        name = f'{prefix}-c{contexts}-s{switch}-a{reuse}'
        result, receipt = invoke(model, trace, profile, variant, [contexts, switch, reuse],
                                 work/(name+'.log'), work)
        audit = study_audit.check(result, trace, baseline, contexts, switch, reuse)
        rejected = study_audit.reject_checks(result, trace, baseline, contexts, switch, reuse)
        actors = result['context_study']['P']
        if contexts == 1:
            observed = deepcopy(result)
            del observed['context_study']
            check(observed == baseline, 'explicit/default context1 complete-result mismatch')
            coverage['explicit_context1_regression'] = True
        else:
            check(all(actor['enabled_calls'] == 1 for actor in actors),
                  'small trace did not invoke both candidate workers')
            check(sum(actor['context_switches'] for actor in actors) == result['M_commands'],
                  'some matrix commands bypassed candidate worker')
            if n == 1:
                empty = actors[1]
                check(all(empty[name] == 0 for name in (
                    'groups', 'A_groups', 'A_loaded_bytes', 'A_saved_bytes',
                    'context_switches', 'completed_contexts', 'psum_register_bytes_peak',
                    'A_bank_peak', 'B_bank_peak')), 'empty P allocated data or work')
                coverage['empty_worker'] = True
            coverage['tail_N'] |= n % 8 != 0
            coverage['tail_K'] |= k % 256 != 0
            coverage['full_16_contexts'] |= any(
                actor['psum_register_bytes_peak'] == 16*96 for actor in actors)
            coverage['group_reuse'] |= any(actor['groups'] > 1 for actor in actors)
            coverage['reuse_disabled'] |= not reuse
        receipt.update(N=n, K=k, bits=bits, profile=profile, variant=variant,
                       contexts=contexts, switch_cycles=switch, reuse_A=bool(reuse),
                       trace=trace.name, trace_sha256=digest(trace), result=result,
                       audit=audit, negative_checks=rejected)
        records.append(receipt)
        (work/(name+'.json')).write_text(json.dumps(receipt, indent=2)+'\n', encoding='utf-8')

    check(all(coverage.values()), 'missing edge coverage: '+str(coverage))
    trace = traces[(1, 4097, 8, 'observe')]
    invalid = [dict(name='context_non_integer', extra=['8junk', '1', '1']),
               dict(name='context_zero', extra=['0', '1', '1']),
               dict(name='context_over_limit', extra=['32', '1', '1']),
               dict(name='negative_switch', extra=['8', '-1', '1']),
               dict(name='invalid_reuse', extra=['8', '1', '2'])]
    invalid_receipts = []
    for item in invalid:
        _, receipt = invoke(model, trace, 'queued_pipe_w8', 'observe', item['extra'],
                            work/('invalid-'+item['name']+'.log'), work, expected_error=True)
        receipt.update(name=item['name'], expected='nonzero exit and explicit invalid context error')
        invalid_receipts.append(receipt)

    report = dict(passed=True, issue=247, output_directory=str(work), model_sha256=digest(model),
                  source_sha256=digest(Path(__file__).resolve()),
                  audit_source_sha256=digest(Path(study_audit.__file__).resolve()),
                  candidate_case_count=len(records), default_baseline_count=len(baseline_receipts),
                  invalid_argument_count=len(invalid_receipts),
                  total_model_invocations=len(records)+len(baseline_receipts)+len(invalid_receipts),
                  coverage=coverage, default_baselines=baseline_receipts,
                  candidate_cases=records, invalid_arguments=invalid_receipts,
                  scope='Actual SystemC candidate execution on empty-P and N/K-tail traces; '
                        'timing/resource/lifetime/traffic audits, not tensor arithmetic or RTL proof')
    (work/'result.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    report = run_edges(args.model, args.out)
    print(json.dumps({k: report[k] for k in ('passed', 'candidate_case_count',
                                           'default_baseline_count', 'invalid_argument_count',
                                           'total_model_invocations', 'coverage')}))
