"""Slurm-only prefill width/bank study, retaining immutable run30 controls."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import importlib.util
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
import traceback
import hashlib

HERE = Path(__file__).resolve().parent
RUN30_SHA = 'a76271fb334081216248ae3f5ad441d56edabdbfaafbdfb28ee4af0ca26162e5'
RUN25_SHA = 'b56095b29aac658af899db495d5b44a07246c3ad04fa93a7b8945def87cfbd03'
RUN25_INPUTS_SHA = 'bb90cbd0e958b76c12bb0474eb039a2799618659bf4b4132adf2361b341c1989'
SCOPE = ('Actual execution of conditional SystemC prefill2 W8 timing, 32KiB pool; '
         'A consumption width and physical read-group schedule only. '
         'No native full-model RTL throughput, physical frequency or quality qualification.')


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def execute(command, log, cwd):
    proc = subprocess.run(list(map(str, command)), cwd=cwd,
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    log.write_bytes(proc.stdout)
    text = proc.stdout.decode(errors='replace')
    require(proc.returncode == 0, 'command failed: ' + repr(list(map(str, command))) + '\n' + text[-3500:])
    return text


def configurations():
    return ([dict(width=w, groups=1, mapping='single') for w in (16, 32, 64, 128)] +
            [dict(width=w, groups=2, mapping=m) for m in ('contiguous', 'striped') for w in (32, 64, 128)])


def config_name(config):
    return 'w{width}-g{groups}-{mapping}'.format(**config)


def old_lookup(prior, item, width):
    keys = ('workload', 'profile', 'variant', 'dual_ports', 'shared_pool_KiB',
            'fifo_beats', 'read_latency_cycles', 'pool_port_cycles')
    found = [c for c in prior['cases'] if c['shared_consumer_bytes_per_cycle'] == width
             and all(c[k] == item[k] for k in keys)]
    require(len(found) == 1, 'run30 unique control missing')
    return found[0]['result']


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    repo, inputs, out = root / 'source', root / 'inputs', root / 'results'
    cpus = int(os.environ.get('SLURM_CPUS_PER_TASK', '0'))
    require(bool(os.environ.get('SLURM_JOB_ID')) and 1 <= cpus <= 4,
            'actual Slurm allocation required; no local/login execution')
    manifest = json.loads((root / 'inputs.json').read_bytes())
    require(re.fullmatch('[0-9a-f]{40}', manifest.get('source_commit', '')) is not None, 'source commit absent')
    for field, base in (('code_sha256', repo), ('input_sha256', root)):
        require(bool(manifest.get(field)), 'empty input lock')
        for name, digest in manifest[field].items():
            require(sha(base / name) == digest, 'deployment drift: ' + name)
    for path in HERE.iterdir():
        if path.is_file() and path.suffix in ('.py', '.hpp', '.inc', '.cpp', '.sh', '.md'):
            name = path.relative_to(repo).as_posix()
            require(manifest['code_sha256'].get(name) == sha(path), 'unlocked experiment source ' + name)
    require(sha(root / 'run30-result.json') == RUN30_SHA, 'run30 identity drift')
    require(sha(root / 'run25-result.json') == RUN25_SHA, 'run25 identity drift')
    require(sha(root / 'run25-inputs.json') == RUN25_INPUTS_SHA, 'run25 manifest identity drift')
    prior = json.loads((root / 'run30-result.json').read_bytes())
    require(prior.get('passed') is True and len(prior['cases']) == 32, 'run30 incomplete')
    frozen_lock = json.loads((root / 'run25-inputs.json').read_bytes())
    for name, digest in frozen_lock['code_sha256'].items():
        if name.startswith('project/experiments/') and Path(name).suffix != '.md':
            require(sha(repo / name) == digest, 'frozen source changed: ' + name)
    for name, digest in frozen_lock['input_sha256'].items():
        require(sha(root / name) == digest, 'frozen input changed: ' + name)
    old_dir = repo / 'project/experiments/shared_pool_study'
    sys.path.insert(0, str(old_dir))
    old = load(old_dir / 'run.py', 'width_frozen_run')
    gen = load(HERE / 'generate.py', 'width_generator')
    derived = load(HERE / 'audit.py', 'width_independent_audit')
    r4_prior = json.loads((root / 'run23-result.json').read_bytes())
    for name, digest in old.audit.FROZEN_INPUTS.items():
        require(sha(root / name) == digest, 'calibration identity changed: ' + name)
    r1, r2, r4 = (root / n for n in ('r1-calibration-result.json', 'r2-calibration-result.json', 'calibration-result.json'))
    out.mkdir(exist_ok=False)
    report = dict(passed=False, scope=SCOPE, source_commit=manifest['source_commit'],
                  manifest_sha256=sha(root / 'inputs.json'), prior_run30_sha256=RUN30_SHA,
                  versions=dict(python=platform.python_version(), SystemC='3.0.2'),
                  slurm=dict(job_id=os.environ['SLURM_JOB_ID'], cpus=cpus),
                  configuration_plan=configurations(), cases=[], generations={}, numeric_checks={},
                  native_full_model_tokens_per_second=None, physical_clock_qualified=False,
                  baseline_phase_passed=False)

    def save():
        (out / 'result.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf8')

    try:
        report['versions']['gcc'] = execute(['g++', '--version'], out / 'gcc.log', out).splitlines()[0]
        prefix = Path('/public/home/yuzelu/opt/systemc-3.0.2-issue219')
        (out / 'm-profile.log').write_bytes((inputs / 'm-profile.log').read_bytes())
        for config in configurations():
            label = config_name(config)
            generated = out / ('generated-' + label)
            receipt = gen.generate(repo, generated, r1, r2, r4, config['width'], config['groups'], config['mapping'])
            report['generations'][label] = receipt
            selected_audit = derived.derive(repo, out / ('audit-' + label + '.py'),
                                            config['width'], config['groups'], config['mapping'])
            binary = out / ('model-' + label)
            execute(['g++', '-std=c++17', '-O2', '-Wall', '-Wextra', '-Werror',
                     generated / 'model.cpp', '-I' + str(generated), '-I' + str(prefix / 'include'),
                     '-L' + str(prefix / 'lib'), '-Wl,-rpath,' + str(prefix / 'lib'),
                     '-lsystemc', '-o', binary], out / ('build-' + label + '.log'), out)
            receipt['binary_sha256'] = sha(binary)
            receipt['derived_audit_sha256'] = sha(out / ('audit-' + label + '.py'))
            numeric_out = out / ('numeric-' + label)
            execute([sys.executable, '-B', HERE / 'check_probe.py', '--repo', repo,
                     '--model', generated, '--out', numeric_out, '--systemc-prefix', prefix,
                     '--width', config['width'], '--groups', config['groups'], '--mapping', config['mapping']],
                    out / ('numeric-' + label + '.log'), out)
            numeric = json.loads((numeric_out / 'result.json').read_bytes())
            require(numeric.get('passed') is True, 'numeric/group/FIFO validation failed')
            require(numeric['model_header_sha256'] == sha(generated / 'shared_pool.hpp'), 'numeric header drift')
            report['numeric_checks'][label] = dict(result=numeric, result_sha256=sha(numeric_out / 'result.json'))

            def case(item):
                name = label + '-' + old.case_name(item)
                log = out / (name + '.log')
                command = old.command(binary, inputs, item)
                text = execute(command, log, out)
                lines = [json.loads(t[7:]) for t in text.splitlines() if t.startswith('RESULT ')]
                require(len(lines) == 1 and 'MODEL_FAILURE' not in text and 'SystemC 3.0.2' in text, 'invalid actual output')
                row = lines[0]
                baseline = old.audit.lookup(r4_prior, item)
                checked = selected_audit.check(row, baseline, inputs / 'prefill2.trace', item)
                rejected = selected_audit.reject_checks(row, baseline, inputs / 'prefill2.trace', item)
                frozen = old_lookup(prior, item, config['width'] if config['width'] in (16, 32) else 32)
                control = config['groups'] == 1 and config['width'] in (16, 32)
                if control:
                    require(row == frozen, 'complete run30 RESULT control differs: ' + name)
                # A port changes must not change external transfers or arithmetic.
                fixed = ('read_bus_bytes', 'write_bus_bytes', 'logical_read_bytes', 'logical_write_bytes',
                         'dma_descriptors', 'M_commands', 'M_tiles', 'M_work_ticks', 'vector_work_ticks', 'adapter_work_ticks')
                for field in fixed:
                    require(row[field] == frozen[field], 'work/traffic changed: ' + field)
                record = dict(item, configuration=config, result=row, audit=checked, negative_checks=rejected,
                              run30_complete_RESULT_exact=(row == frozen), run30_control_required=control,
                              command=list(map(str, command)), log_sha256=sha(log), exit_code=0)
                (out / (name + '.json')).write_text(json.dumps(record, indent=2) + '\n', encoding='utf8')
                print('WIDTH_CASE ' + name + ' token_s=' + str(row['tokens_per_second']), flush=True)
                return record

            pools = (0, 32) if config['groups'] == 1 and config['width'] in (16, 32) else (32,)
            items = [old.configuration('prefill2', 'queued_pipe_w8', 'adaptive_prefix_pair_combine', dual, pool)
                     for pool in pools for dual in (False, True)]
            with ThreadPoolExecutor(max_workers=cpus) as workers:
                for record in workers.map(case, items):
                    report['cases'].append(record)
                    save()
            if config == dict(width=32, groups=1, mapping='single'):
                report['baseline_phase_passed'] = True
            save()
        require(len(report['cases']) == 24, 'incomplete planned sweep')
        report['summary'] = [dict(configuration=c['configuration'], dual_ports=c['dual_ports'],
                                  tokens_per_second=c['result']['tokens_per_second'],
                                  seconds=c['result']['seconds'],
                                  shared_pool=c['result']['shared_pool_study'])
                             for c in report['cases'] if c['shared_pool_KiB'] == 32]
        report['passed'] = True
        (out / 'summary.json').write_text(json.dumps(dict(scope=SCOPE, cases=report['summary']), indent=2) + '\n', encoding='utf8')
    except Exception as exc:
        report.update(error=str(exc), traceback=traceback.format_exc())
    report['output_sha256'] = {p.relative_to(out).as_posix(): sha(p) for p in out.rglob('*')
                              if p.is_file() and p != out / 'result.json'}
    save()
    print(json.dumps(dict(passed=report['passed'], cases=len(report['cases']), result=str(out / 'result.json'))), flush=True)
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
