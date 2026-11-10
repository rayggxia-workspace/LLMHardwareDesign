"""Slurm-only actual SystemC shared-pool sweep; frozen R4 is the control."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
import traceback

import audit
from generate_shared_pool import generate

HERE = Path(__file__).resolve().parent
WORK = [
    ('decode512', 'queued_pipe_w8', 'adaptive_prefix_pair_combine'),
    ('decode512', 'queued_pipe_w16', 'adaptive'),
    ('decode2048', 'queued_pipe_w8', 'adaptive_prefix_pair_combine'),
    ('prefill2', 'queued_pipe_w8', 'adaptive_prefix_pair_combine'),
]


def configuration(workload, profile, variant, dual, pool, fifo=4, latency=2,
                  port_cycles=1, purpose='main'):
    return dict(workload=workload, profile=profile, variant=variant,
                dual_ports=dual, shared_pool_KiB=pool, fifo_beats=fifo,
                read_latency_cycles=latency, pool_port_cycles=port_cycles,
                contexts=8, P_KiB=16, switch_cycles=1, reuse_A=True,
                P_port_quarters=4, policy_KiB=0, R1_enabled=True,
                R2_enabled=True, iteration4_enabled=True, purpose=purpose)


def plan():
    return [configuration(w, p, v, dual, pool)
            for pool in (0, 32, 48, 96) for w, p, v in WORK
            for dual in (False, True)]


def sensitivity_plan():
    w, p, v = WORK[0]
    result = [configuration(w, p, v, True, 48, fifo, latency, port, 'sensitivity')
              for fifo, latency, port in
              ((1, 2, 1), (8, 2, 1), (4, 0, 1), (4, 8, 1), (4, 2, 2), (4, 2, 4))]
    w, p, v = WORK[3]
    result += [configuration(w, p, v, True, 96, fifo, latency, port, 'sensitivity')
               for fifo, latency, port in ((1, 2, 1), (4, 8, 1), (4, 2, 2), (4, 2, 4))]
    return result


def case_name(item):
    return '{}-{}-{}-pool{}-f{}-l{}-p{}'.format(
        item['workload'], item['profile'],
        'idealdual' if item['dual_ports'] else 'shared', item['shared_pool_KiB'],
        item['fifo_beats'], item['read_latency_cycles'], item['pool_port_cycles'])


def command(binary, inputs, item):
    return [binary, inputs / (item['workload'] + '.trace'), item['profile'],
            item['variant'], 8, 1, 1, 16, int(item['dual_ports']), 4, 0, 1, 1, 1,
            item['shared_pool_KiB'], item['fifo_beats'],
            item['read_latency_cycles'], item['pool_port_cycles']]


def execute(cmd, log, cwd, expected=0, env=None):
    process = subprocess.run(list(map(str, cmd)), cwd=cwd, env=env,
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    log.write_bytes(process.stdout)
    text = process.stdout.decode(errors='replace')
    if process.returncode != expected:
        raise RuntimeError(str(list(map(str, cmd))) + ' exit ' +
                           str(process.returncode) + '\n' + text[-3000:])
    return text


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    repo, inputs, out = root / 'source', root / 'inputs', root / 'results'
    cpus = int(os.environ.get('SLURM_CPUS_PER_TASK', '0'))
    audit.require(bool(os.environ.get('SLURM_JOB_ID')) and 1 <= cpus <= 4,
                  'actual Slurm 1..4 CPU allocation required')
    manifest = json.loads((root / 'inputs.json').read_bytes())
    audit.require(re.fullmatch('[0-9a-f]{40}', manifest.get('source_commit', ''))
                  is not None, 'source commit absent')
    for field, base in (('code_sha256', repo), ('input_sha256', root)):
        audit.require(bool(manifest.get(field)), 'empty deployment lock ' + field)
        for name, digest in manifest[field].items():
            audit.require(audit.sha(base / name) == digest, 'deployment SHA drift ' + name)
    for name, digest in audit.FROZEN_INPUTS.items():
        audit.require(audit.sha(root / name) == digest, 'frozen prerequisite changed ' + name)
    prior = json.loads((root / 'run23-result.json').read_bytes())
    audit.require(prior.get('passed') is True and prior.get('baseline_phase_passed') is True
                  and len(prior['cases']) == 16, 'actual run23 R4 baseline incomplete')
    for name, digest in prior['input_sha256'].items():
        audit.require(audit.sha(inputs / name) == digest, 'old input drift ' + name)
    audit.require(json.loads((HERE / 'plan.json').read_bytes()) ==
                  dict(main=plan(), sensitivity=sensitivity_plan()), 'shared-pool plan drift')
    r1, r2, r4 = (root / name for name in (
        'r1-calibration-result.json', 'r2-calibration-result.json', 'calibration-result.json'))
    frozen = audit.frozen_r4(str(repo))
    profile = frozen.read_calibration(r4, repo)
    audit.require(json.loads(json.dumps(profile)) == prior['R4_calibration'], 'actual run22 R4 calibration drift')
    out.mkdir(exist_ok=False)
    report = dict(passed=False, source_commit=manifest['source_commit'],
                  manifest_sha256=audit.sha(root / 'inputs.json'), scope=audit.SCOPE,
                  prior_run23_sha256=audit.RUN23_SHA, input_sha256=prior['input_sha256'],
                  R4_calibration=profile, baseline_phase_passed=False,
                  versions=dict(python=platform.python_version(), SystemC='3.0.2'),
                  slurm=dict(job_id=os.environ['SLURM_JOB_ID'], cpus=cpus),
                  unchanged_hardware=prior['unchanged_hardware'],
                  layers=prior['layers'], cases=[], sensitivity_cases=[],
                  area_budget={str(k): audit.area_budget(k, 4) for k in (0, 32, 48, 96)},
                  physical_clock_qualified=False, full_LLM_RTL_numeric_proof=False)

    def save():
        (out / 'result.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf8')

    try:
        report['versions']['gcc'] = execute(['g++', '--version'], out / 'gcc-version.log', out).splitlines()[0]
        generated = out / 'generated'
        generation = generate(repo, generated, r1, r2, r4)
        audit.require(generation['round4_generated_sha256'] == prior['generation']['generated_sha256'],
                      'frozen R4 generated source differs from actual run23')
        report['generation'] = generation
        report['round4_generated_exact'] = True
        (out / 'm-profile.log').write_bytes((inputs / 'm-profile.log').read_bytes())
        prefix = Path('/public/home/yuzelu/opt/systemc-3.0.2-issue219')
        flags = ['-std=c++17', '-O2', '-Wall', '-Wextra', '-Werror']
        execute(['g++', *flags, generated / 'model.cpp', '-I' + str(generated),
                 '-I' + str(prefix / 'include'), '-L' + str(prefix / 'lib'),
                 '-Wl,-rpath,' + str(prefix / 'lib'), '-lsystemc', '-o', out / 'model'],
                out / 'build.log', out)
        report['model_binary_sha256'] = audit.sha(out / 'model')
        upstream = repo / 'project/experiments/p_dma_study/upstream'
        execute(['g++', *flags, upstream / 'kernel_probe.cpp', '-o', out / 'kernel_probe'],
                out / 'kernel-build.log', out)
        env = dict(os.environ, BLOCK_STUDY_MODEL=str(out / 'model'))
        env.pop('U_FUSION_EVENTS', None)
        env.pop('U_FUSION_TRACE_SHA256', None)
        legacy = []
        for script in ('check_kernels.py', 'validate.py', 'smoke.py'):
            cmd = [sys.executable, '-B', upstream / script]
            log = out / (script + '.log')
            execute(cmd, log, out, env=env)
            legacy.append(dict(command=list(map(str, cmd)), exit_code=0,
                               log=log.name, log_sha256=audit.sha(log)))
        report['legacy_checks'] = legacy
        numeric_cmd = [sys.executable, '-B', HERE / 'numeric_check.py',
                       '--model', generated, '--out', out / 'numeric',
                       '--cxx', 'g++', '--systemc-prefix', prefix]
        execute(numeric_cmd, out / 'numeric-check.log', out)
        numeric = json.loads((out / 'numeric/result.json').read_bytes())
        audit.require(numeric.get('passed') is True, 'shared FIFO numeric/service check failed')
        audit.require(numeric['model_header_sha256'] == audit.sha(generated / 'shared_pool.hpp'),
                      'numeric probe did not use the actual generated shared pool')
        audit.require({'input.txt', 'events.jsonl'} <= set(numeric['artifact_sha256']),
                      'numeric input/service event evidence absent')
        for name, digest in numeric['artifact_sha256'].items():
            audit.require(audit.sha(out / 'numeric' / name) == digest, 'numeric artifact SHA drift ' + name)
        for name, digest in numeric['source_sha256'].items():
            audit.require(audit.sha(HERE / name) == digest, 'numeric oracle source SHA drift ' + name)
        report['numeric_check'] = dict(command=list(map(str, numeric_cmd)), exit_code=0,
                                       result=numeric, result_sha256=audit.sha(out / 'numeric/result.json'),
                                       log_sha256=audit.sha(out / 'numeric-check.log'))

        def case(item):
            name = case_name(item)
            cmd = command(out / 'model', inputs, item)
            log = out / (name + '.log')
            text = execute(cmd, log, out)
            rows = [json.loads(line[7:]) for line in text.splitlines() if line.startswith('RESULT ')]
            audit.require(len(rows) == 1 and 'MODEL_FAILURE' not in text and
                          'SystemC 3.0.2' in text, 'invalid actual shared-pool model output')
            baseline = audit.lookup(prior, item)
            args = (baseline, inputs / (item['workload'] + '.trace'), item)
            checked = audit.check(rows[0], *args)
            negative = audit.reject_checks(rows[0], *args)
            record = dict(item, result=rows[0], audit=checked, negative_checks=negative,
                          command=list(map(str, cmd)), exit_code=0,
                          speedup_vs_same_layer_R4=baseline['seconds'] / rows[0]['seconds'],
                          log_sha256=audit.sha(log), area_budget=audit.area_budget(
                              item['shared_pool_KiB'], item['fifo_beats']))
            (out / (name + '.json')).write_text(json.dumps(record, indent=2) + '\n', encoding='utf8')
            print('SHARED_POOL_CASE ' + name + ' tokens_s=' + str(rows[0]['tokens_per_second']), flush=True)
            return record

        # Establish exact controls before producing any speedup claims.
        for pool_kib in (0, 32, 48, 96):
            items = [item for item in plan() if item['shared_pool_KiB'] == pool_kib]
            with ThreadPoolExecutor(max_workers=cpus) as workers:
                for record in workers.map(case, items):
                    report['cases'].append(record)
                    save()
            if pool_kib == 0:
                report['baseline_phase_passed'] = True
                save()
        with ThreadPoolExecutor(max_workers=cpus) as workers:
            for record in workers.map(case, sensitivity_plan()):
                report['sensitivity_cases'].append(record)
                save()

        invalid = []
        # Test lexical as well as range validation. No malformed input may emit RESULT.
        for field, index, values in (
                ('pool', -4, ('-1', '1', '64', '32junk')),
                ('FIFO', -3, ('0', '3', '-1', '4junk')),
                ('latency', -2, ('-1', '17', '2junk')),
                ('port', -1, ('0', '3', '1junk'))):
            for value in values:
                cmd = command(out / 'model', inputs, plan()[8])
                cmd[index] = value
                log = out / ('invalid-' + str(len(invalid)) + '.log')
                text = execute(cmd, log, out, expected=2)
                audit.require('RESULT ' not in text, 'invalid shared-pool CLI emitted result')
                invalid.append(dict(field=field, value=value, exit_code=2, log_sha256=audit.sha(log)))
        report['invalid_CLI_rejected'] = invalid
        audit.require(len(report['cases']) == 32 and len(report['sensitivity_cases']) == 10,
                      'incomplete main/sensitivity sweep')
        equivalents = []
        for w, p, v in WORK:
            for dual in (False, True):
                pair = [next(c for c in report['cases'] if c['workload'] == w and c['profile'] == p
                             and c['dual_ports'] is dual and c['shared_pool_KiB'] == capacity)
                        for capacity in (48, 96)]
                facts = [c['audit']['trace'] for c in pair]
                same_coverage = facts[0]['operations'] == facts[1]['operations']
                compared = [deepcopy(c['result']) for c in pair]
                for result in compared:
                    result['shared_pool_study'].pop('capacity_bytes')
                equivalents.append(dict(workload=w, profile=p, dual_ports=dual,
                                        pool_KiB=[48, 96], same_operation_A_coverage=same_coverage,
                                        all_result_fields_except_capacity_equal=compared[0] == compared[1],
                                        tokens_per_second=[c['result']['tokens_per_second'] for c in pair],
                                        interpretation=('same resident A extents and fixed port contract; any timing difference needs investigation'
                                                        if same_coverage else 'different resident A coverage; compare measured timing')))
        report['same_working_set_comparisons'] = equivalents
        summary = [dict(workload=c['workload'], profile=c['profile'], dual_ports=c['dual_ports'],
                        pool_KiB=c['shared_pool_KiB'], tokens_per_second=c['result']['tokens_per_second'],
                        seconds=c['result']['seconds'], speedup=c['speedup_vs_same_layer_R4'],
                        DDR_read_bytes=c['result']['read_bus_bytes'],
                        macro_proxy_delta_mm2=c['area_budget']['additional_macro_proxy_mm2'])
                   for c in report['cases']]
        report['summary'] = summary
        report['passed'] = True
        sensitivity_summary = [dict(workload=c['workload'], profile=c['profile'], dual_ports=c['dual_ports'],
                                    pool_KiB=c['shared_pool_KiB'], fifo_beats=c['fifo_beats'],
                                    read_latency_cycles=c['read_latency_cycles'], pool_port_cycles=c['pool_port_cycles'],
                                    tokens_per_second=c['result']['tokens_per_second'],
                                    speedup_vs_R4=c['speedup_vs_same_layer_R4'],
                                    pool=c['result']['shared_pool_study']) for c in report['sensitivity_cases']]
        (out / 'summary.json').write_text(json.dumps(dict(scope=audit.SCOPE, cases=summary,
                 sensitivity=sensitivity_summary, same_working_set=equivalents), indent=2) + '\n')
        lines = ['workload,profile,dual_ports,pool_KiB,tokens_per_second,seconds,speedup,DDR_read_bytes,macro_proxy_delta_mm2']
        lines += [','.join(str(c[k]) for k in ('workload', 'profile', 'dual_ports', 'pool_KiB',
                    'tokens_per_second', 'seconds', 'speedup', 'DDR_read_bytes', 'macro_proxy_delta_mm2')) for c in summary]
        (out / 'summary.csv').write_text('\n'.join(lines) + '\n')
    except Exception as error:
        report['error'] = repr(error)
        report['traceback'] = traceback.format_exc()
        raise
    finally:
        save()
    print('SHARED_POOL_PASS32_SENSITIVITY10', flush=True)


if __name__ == '__main__':
    main()
