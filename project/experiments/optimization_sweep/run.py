"""Slurm-only controlled optimization sweep. Production RTL is untouched."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import json
import math
import os
from pathlib import Path
import platform
import sys
import traceback

from generate import generate, load, sha

HERE = Path(__file__).resolve().parent
CASES = ('base', 'vector8', 'vector16', 'nexp8', 'm16', 'feed2', 'ddr25p6',
         'ddr34p2', 'pool48', 'pool96', 'write16', 'm16_feed2',
         'vector16_nexp8', 'compute_bundle')
WORK = (('decode512', 'queued_pipe_w8', 'adaptive_prefix_pair_combine'),
        ('decode512', 'queued_pipe_w16', 'adaptive'),
        ('decode2048', 'queued_pipe_w8', 'adaptive_prefix_pair_combine'),
        ('prefill2', 'queued_pipe_w8', 'adaptive_prefix_pair_combine'))


def require(value, message):
    if not value:
        raise ValueError(message)


def check(row, reference, name, pool):
    m = row['optimization_sweep']
    require(m['case'] == name and m['timing_sensitivity_only'] is True, 'scope/case mismatch')
    require(m['candidate_RTL_calibrated'] is False and m['native_full_model_tokens_per_second'] is None,
            'candidate falsely calibrated')
    for field in ('read_bus_bytes', 'write_bus_bytes', 'logical_read_bytes', 'logical_write_bytes',
                  'dma_descriptors', 'M_commands', 'M_tiles', 'KV_state_write_bytes',
                  'cache_hits', 'cache_misses', 'dirty_evictions', 'dead_lines_discarded'):
        require(row[field] == reference[field], 'work/traffic changed: ' + field)
    require(row['M_work_ticks'] == reference['M_work_ticks']-m['compute_old']+m['compute_new'], 'M work conservation')
    require(m['compute_old']+m['tail_cycles'] == reference['M_work_ticks'], 'M body/tail accounting')
    require(row['adapter_work_ticks'] == reference['adapter_work_ticks']-m['adapt_old']+m['adapt_new'], 'adapter conservation')
    require(row['vector_work_ticks'] == reference['vector_work_ticks']-m['vector_old']+m['vector_new']-m['nexp_old']+m['nexp_new'], 'U work conservation')
    require(m['vector_new'] <= m['vector_old'] and m['nexp_new'] <= m['nexp_old'], 'U negative cost savings')
    require(m['compute_new'] <= m['compute_old'] and m['adapt_new'] <= m['adapt_old'], 'M negative cost savings')
    require(m['result_new'] >= m['result_old'] and m['result_bytes'] > 0, 'result write conservation')
    expected_rate = row['tokens'] / row['seconds']
    require(math.isclose(row['tokens_per_second'], expected_rate, rel_tol=1e-10), 'token rate arithmetic')
    require(abs(row['seconds']*300e6-row['ticks']) <= 1.1, 'clock/tick arithmetic')
    require(row['max_outstanding_beats'] <= 32 and row['max_descriptor_queue'] <= 32, 'DDR credits exceeded')
    p = row['shared_pool_study']
    require(p['capacity_bytes'] == pool*1024 and p['peak_bytes'] <= pool*1024, 'pool capacity exceeded')
    require(p['live_epoch'] == 0 and p['live_workers'] == 0, 'unfinished pool lifecycle')
    require(p['fill_peak_descriptors'] <= 2, 'fill credit limit')
    for worker in p['P']:
        require(worker['fifo_peak'] <= 4 and worker['active'] == 0, 'pool FIFO leak/overflow')
        require(worker['read_bytes'] == worker['consumed_bytes'], 'pool bytes lost')
    clean = deepcopy(row); clean.pop('optimization_sweep')
    if name in ('base', 'pool48', 'pool96'):
        require(clean == reference, 'complete historical RESULT mismatch')
    return dict(work_conservation=True, finite_resources=True, rate_arithmetic=True,
                complete_historical_RESULT_exact=clean == reference)


def negative_checks(row, reference, name, pool):
    checks = []
    for field in ('read_bus_bytes', 'M_commands', 'M_work_ticks', 'vector_work_ticks', 'tokens_per_second'):
        bad = deepcopy(row); bad[field] += 1
        try:
            check(bad, reference, name, pool)
        except ValueError:
            checks.append(field)
        else:
            raise AssertionError('tampered result accepted: ' + field)
    return checks


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--root', type=Path, required=True)
    root = parser.parse_args().root.resolve()
    repo, inputs, out = root/'source', root/'inputs', root/'results'
    cpus = int(os.environ.get('SLURM_CPUS_PER_TASK', 0))
    require(bool(os.environ.get('SLURM_JOB_ID')) and 1 <= cpus <= 4, 'real Slurm 1..4 CPUs required')
    manifest = json.loads((root/'inputs.json').read_bytes())
    for field, base in (('code_sha256', repo), ('input_sha256', root)):
        for name, digest in manifest[field].items():
            require(sha(base/name) == digest, 'deployment source/input drift '+name)
    sys.path.insert(0, str(repo/'project/experiments/shared_pool_study'))
    old = load(repo/'project/experiments/shared_pool_study/run.py', 'optimization_frozen_run')
    require(sha(root/'run25-result.json') == 'b56095b29aac658af899db495d5b44a07246c3ad04fa93a7b8945def87cfbd03', 'run25 result drift')
    prior = json.loads((root/'run25-result.json').read_bytes())
    lock = json.loads((root/'run25-inputs.json').read_bytes())
    for name, digest in lock['code_sha256'].items():
        if name.startswith('project/experiments/') and Path(name).suffix != '.md':
            require(sha(repo/name) == digest, 'frozen dependency changed '+name)
    for name, digest in lock['input_sha256'].items():
        require(sha(root/name) == digest, 'frozen input changed '+name)
    out.mkdir(exist_ok=False)
    report = dict(passed=False, source_commit=manifest['source_commit'],
                  scope='OLD 300MHz/2P1U/S32-K256-S96 conditional model timing sensitivities; no production RTL change',
                  native_full_model_tokens_per_second=None, physical_clock_qualified=False,
                  cases=[], plan=list(CASES), baseline_phase_passed=False,
                  versions=dict(python=platform.python_version(), SystemC='3.0.2'),
                  manifest_sha256=sha(root/'inputs.json'), slurm=dict(job=os.environ['SLURM_JOB_ID'], cpus=cpus))

    def save():
        (out/'result.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf8')

    try:
        generated = out/'generated'
        report['generation'] = generate(repo, generated, root/'r1-calibration-result.json',
                                        root/'r2-calibration-result.json', root/'calibration-result.json')
        prefix = Path('/public/home/yuzelu/opt/systemc-3.0.2-issue219')
        report['versions']['gcc'] = old.execute(['g++', '--version'], out/'gcc.log', out).splitlines()[0]
        compile_cmd = ['g++', '-std=c++17', '-O2', '-Wall', '-Wextra', '-Werror', generated/'model.cpp',
                       '-I'+str(generated), '-I'+str(prefix/'include'), '-L'+str(prefix/'lib'),
                       '-Wl,-rpath,'+str(prefix/'lib'), '-lsystemc', '-o', out/'model']
        old.execute(compile_cmd, out/'build.log', out)
        report['compile_command'] = list(map(str, compile_cmd)); report['binary_sha256'] = sha(out/'model')
        (out/'m-profile.log').write_bytes((inputs/'m-profile.log').read_bytes())
        numeric_cmd = [sys.executable, '-B', HERE/'probe.py', '--repo', repo, '--model', generated, '--out', out/'numeric']
        old.execute(numeric_cmd, out/'numeric.log', out)
        report['numeric'] = json.loads((out/'numeric/result.json').read_bytes())
        require(report['numeric']['passed'], 'numeric/FIFO probe failed')

        def case(task):
            name, work, profile, variant, dual = task
            pool = 48 if name == 'pool48' else 96 if name == 'pool96' else 32
            item = old.configuration(work, profile, variant, dual, pool)
            key = name+'-'+old.case_name(item)
            matches = [x for x in prior['cases'] if all(x[k] == item[k] for k in ('workload','profile','variant','dual_ports','shared_pool_KiB'))]
            require(len(matches) == 1, 'reference case missing')
            ref = matches[0]['result']
            env = dict(os.environ, OPTIMIZATION_CASE=name)
            env.pop('U_FUSION_EVENTS', None); env.pop('U_FUSION_TRACE_SHA256', None)
            cmd = old.command(out/'model', inputs, item)
            text = old.execute(cmd, out/(key+'.log'), out, env=env)
            rows = [json.loads(line[7:]) for line in text.splitlines() if line.startswith('RESULT ')]
            require(len(rows) == 1 and 'MODEL_FAILURE' not in text and 'SystemC 3.0.2' in text, 'invalid SystemC result')
            row = rows[0]
            checked = check(row, ref, name, pool)
            negatives = negative_checks(row, ref, name, pool)
            result = dict(item, optimization=name, result=row, audit=checked, negative_checks=negatives,
                          command=list(map(str, cmd)), environment={'OPTIMIZATION_CASE': name},
                          log_sha256=sha(out/(key+'.log')), exit_code=0)
            (out/(key+'.json')).write_text(json.dumps(result, indent=2)+'\n', encoding='utf8')
            print('OPT_CASE '+key+' token_s='+str(row['tokens_per_second']), flush=True)
            return result

        for names in (('base',), CASES[1:]):
            tasks = [(name, w, p, v, d) for name in names for w,p,v in WORK for d in (False, True)]
            with ThreadPoolExecutor(max_workers=cpus) as workers:
                for record in workers.map(case, tasks):
                    report['cases'].append(record); save()
            report['baseline_phase_passed'] = True; save()
        require(len(report['cases']) == len(CASES)*8, 'incomplete sweep')
        invalid = dict(os.environ, OPTIMIZATION_CASE='unsupported')
        old.execute(old.command(out/'model', inputs, old.configuration(*WORK[0], False, 32)),
                    out/'invalid-case.log', out, expected=2, env=invalid)
        report['invalid_case_rejected'] = True; report['passed'] = True
    except Exception as exc:
        report.update(error=str(exc), traceback=traceback.format_exc())
    report['output_sha256'] = {p.relative_to(out).as_posix(): sha(p) for p in out.rglob('*')
                              if p.is_file() and p != out/'result.json'}
    save(); print(json.dumps(dict(passed=report['passed'], cases=len(report['cases']), result=str(out/'result.json'))), flush=True)
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
