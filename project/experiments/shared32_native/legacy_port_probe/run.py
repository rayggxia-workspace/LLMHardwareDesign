"""Slurm-only 16/32 B/clock shared-consumer sensitivity in the OLD metric."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
import traceback

from generate import derive_audit, generate, load, sha

HERE = Path(__file__).resolve().parent
RUN25_SHA = 'b56095b29aac658af899db495d5b44a07246c3ad04fa93a7b8945def87cfbd03'
RUN25_MANIFEST_SHA = 'bb90cbd0e958b76c12bb0474eb039a2799618659bf4b4132adf2361b341c1989'
RUN25_COMMIT = 'a8e793e4c6f97e9dca5b0cc203797dcd3b0e0e78'
SCOPE = ('OLD R4/shared-pool conditional metric: shared A consumer width only, '
         '32 -> 16 B/clock; unchanged S32/K256/S96 arithmetic and existing overlap. '
         'Not measured native full-model RTL throughput or physical qualification.')
LIMITATIONS = [
    'No native S32-to-three-S16-limb conversion, native packed-capacity or K32 command lowering.',
    'No measured descriptor/BEGIN/SEAL/RELEASE or P LOAD join overhead added.',
    'Original byte-masked fill bridge and its two 1024B DDR descriptors remain conditional.',
    'Only shared consumer width changes; local A suffix, B, M and aggregate overlap remain frozen.',
    'Shared and ideal-dual LOCAL port layers are old conditional contracts, not qualification of the new local SRAM RTL.',
    '300MHz remains an assumption; no physical closure or real model-weight/token generation proof.',
]


def require(ok, message):
    if not ok:
        raise ValueError(message)


def execute(cmd, log, cwd, env=None):
    process = subprocess.run(list(map(str, cmd)), cwd=cwd, env=env,
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    log.write_bytes(process.stdout)
    text = process.stdout.decode(errors='replace')
    require(process.returncode == 0,
            'command failed ' + repr(list(map(str, cmd))) + '\n' + text[-3000:])
    return text


def lookup(report, item):
    keys = ('workload', 'profile', 'variant', 'dual_ports', 'shared_pool_KiB',
            'fifo_beats', 'read_latency_cycles', 'pool_port_cycles')
    found = [row for row in report['cases'] if all(row[k] == item[k] for k in keys)]
    require(len(found) == 1, 'missing unique frozen run25 case')
    return found[0]['result']


def check_inputs(root, repo):
    manifest = json.loads((root / 'inputs.json').read_bytes())
    require(re.fullmatch('[0-9a-f]{40}', manifest.get('source_commit', '')) is not None,
            'missing current source commit')
    for field, base in (('code_sha256', repo), ('input_sha256', root)):
        require(bool(manifest.get(field)), 'empty deployment lock ' + field)
        for name, digest in manifest[field].items():
            require(sha(base / name) == digest, 'deployment SHA drift ' + name)
    for path in HERE.iterdir():
        if path.is_file() and path.suffix in ('.py', '.sh', '.md'):
            relative = path.relative_to(repo).as_posix()
            require(manifest['code_sha256'].get(relative) == sha(path),
                    'probe source missing from deployment lock ' + relative)
    require(sha(root / 'run25-result.json') == RUN25_SHA, 'run25 result identity drift')
    require(sha(root / 'run25-inputs.json') == RUN25_MANIFEST_SHA, 'run25 source/input manifest drift')
    lock = json.loads((root / 'run25-inputs.json').read_bytes())
    require(lock['source_commit'] == RUN25_COMMIT, 'frozen source commit drift')
    # Executable experimental code is frozen. Later result prose and current
    # production RTL may legitimately differ from the run25 source snapshot.
    for name, digest in lock['code_sha256'].items():
        if name.startswith('project/experiments/') and Path(name).suffix != '.md':
            require(sha(repo / name) == digest, 'frozen experiment changed ' + name)
    for name, digest in lock['input_sha256'].items():
        require(sha(root / name) == digest, 'run25 input identity drift ' + name)
    prior = json.loads((root / 'run25-result.json').read_bytes())
    require(prior.get('passed') is True and prior.get('baseline_phase_passed') is True
            and len(prior['cases']) == 32, 'run25 not a complete passing baseline')
    for name, digest in prior['input_sha256'].items():
        require(sha(root / 'inputs' / name) == digest, 'trace/profile identity drift ' + name)
    return manifest, prior


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    repo, inputs, out = root / 'source', root / 'inputs', root / 'results'
    cpus = int(os.environ.get('SLURM_CPUS_PER_TASK', '0'))
    require(bool(os.environ.get('SLURM_JOB_ID')) and 1 <= cpus <= 4,
            'actual Slurm allocation of 1..4 CPUs required')
    manifest, prior = check_inputs(root, repo)
    frozen_dir = repo / 'project/experiments/shared_pool_study'
    # The frozen run module imports its sibling audit/generator by module name.
    sys.path.insert(0, str(frozen_dir))
    old = load(frozen_dir / 'run.py', 'frozen_shared_run')
    audit = old.audit
    for name, digest in audit.FROZEN_INPUTS.items():
        require(sha(root / name) == digest, 'frozen prerequisite drift ' + name)
    r4_prior = json.loads((root / 'run23-result.json').read_bytes())
    r1, r2, r4 = (root / name for name in (
        'r1-calibration-result.json', 'r2-calibration-result.json', 'calibration-result.json'))
    items = [item for item in old.plan() if item['shared_pool_KiB'] in (0, 32)]
    require(len(items) == 16, 'old four-workload/two-layer plan drift')
    out.mkdir(exist_ok=False)
    report = dict(passed=False, source_commit=manifest['source_commit'], scope=SCOPE,
                  limitations=LIMITATIONS, run25_source_commit=RUN25_COMMIT,
                  run25_result_sha256=RUN25_SHA, run25_manifest_sha256=RUN25_MANIFEST_SHA,
                  input_sha256=prior['input_sha256'], manifest_sha256=sha(root / 'inputs.json'),
                  versions=dict(python=platform.python_version(), SystemC='3.0.2'),
                  slurm=dict(job_id=os.environ['SLURM_JOB_ID'], cpus=cpus),
                  native_full_model_tokens_per_second=None, physical_clock_qualified=False,
                  cases=[], generations={}, numeric_checks={}, baseline_phase_passed=False)

    def save():
        (out / 'result.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf8')

    try:
        report['versions']['gcc'] = execute(['g++', '--version'], out / 'gcc.log', out).splitlines()[0]
        prefix = Path('/public/home/yuzelu/opt/systemc-3.0.2-issue219')
        flags = ['-std=c++17', '-O2', '-Wall', '-Wextra', '-Werror']
        (out / 'm-profile.log').write_bytes((inputs / 'm-profile.log').read_bytes())
        for width in (32, 16):
            generated = out / ('generated-' + str(width))
            receipt = generate(repo, generated, r1, r2, r4, width)
            require(receipt['frozen_generation']['generated_sha256'] == prior['generation']['generated_sha256'],
                    'frozen generated model differs from actual run25')
            report['generations'][str(width)] = receipt
            this_audit = derive_audit(frozen_dir / 'audit.py', out / ('audit_' + str(width) + '.py'), width)
            binary = out / ('model-' + str(width))
            execute(['g++', *flags, generated / 'model.cpp', '-I' + str(generated),
                     '-I' + str(prefix / 'include'), '-L' + str(prefix / 'lib'),
                     '-Wl,-rpath,' + str(prefix / 'lib'), '-lsystemc', '-o', binary],
                    out / ('build-' + str(width) + '.log'), out)
            report['generations'][str(width)]['binary_sha256'] = sha(binary)
            report['generations'][str(width)]['derived_audit_sha256'] = sha(out / ('audit_' + str(width) + '.py'))
            numeric_out = out / ('numeric-' + str(width))
            execute([sys.executable, '-B', frozen_dir / 'numeric_check.py', '--model', generated,
                     '--out', numeric_out, '--cxx', 'g++', '--systemc-prefix', prefix],
                    out / ('numeric-' + str(width) + '.log'), out)
            numeric = json.loads((numeric_out / 'result.json').read_bytes())
            require(numeric.get('passed') is True and
                    numeric['model_header_sha256'] == sha(generated / 'shared_pool.hpp'),
                    'actual generated header numeric/address check failed')
            count = 0
            with (numeric_out / 'events.jsonl').open(encoding='utf8') as events:
                for line in events:
                    event = json.loads(line)
                    if event['kind'] == 'consume':
                        require(0 < event['bytes'] <= width, 'consumer event exceeds selected width')
                        count += 1
            require(count > 0, 'no actual feeder events')
            report['numeric_checks'][str(width)] = dict(
                result_sha256=sha(numeric_out / 'result.json'), result=numeric,
                selected_width_event_count=count, selected_width_bound_passed=True)

            def case(item):
                name = str(width) + 'B-' + old.case_name(item)
                log = out / (name + '.log')
                command = old.command(binary, inputs, item)
                text = execute(command, log, out)
                rows = [json.loads(line[7:]) for line in text.splitlines() if line.startswith('RESULT ')]
                require(len(rows) == 1 and 'MODEL_FAILURE' not in text and 'SystemC 3.0.2' in text,
                        'invalid actual model output')
                row = rows[0]
                r4_base = audit.lookup(r4_prior, item)
                checked = this_audit.check(row, r4_base, inputs / (item['workload'] + '.trace'), item)
                negative = this_audit.reject_checks(row, r4_base, inputs / (item['workload'] + '.trace'), item)
                prior_row = lookup(prior, item)
                exact = row == prior_row
                if width == 32 or item['shared_pool_KiB'] == 0:
                    require(exact, 'complete RESULT differs from frozen run25 control ' + name)
                record = dict(item, shared_consumer_bytes_per_cycle=width, result=row,
                              audit=checked, negative_checks=negative, run25_all_fields_exact=exact,
                              command=list(map(str, command)), exit_code=0, log_sha256=sha(log))
                (out / (name + '.json')).write_text(json.dumps(record, indent=2) + '\n', encoding='utf8')
                print('PORT_PROBE_CASE ' + name + ' tokens_s=' + str(row['tokens_per_second']), flush=True)
                return record

            for pool in (0, 32):
                with ThreadPoolExecutor(max_workers=cpus) as workers:
                    for record in workers.map(case, [item for item in items if item['shared_pool_KiB'] == pool]):
                        report['cases'].append(record)
                        save()
            if width == 32:
                report['baseline_phase_passed'] = True
                save()
        require(len(report['cases']) == 32, 'incomplete sweep')
        summaries = []
        for item in items:
            if not item['shared_pool_KiB']:
                continue
            old_row = lookup(prior, item)
            new_row = lookup(dict(cases=[c for c in report['cases'] if c['shared_consumer_bytes_per_cycle'] == 16]), item)
            baseline = audit.lookup(r4_prior, item)
            summaries.append(dict(workload=item['workload'], profile=item['profile'],
                dual_ports=item['dual_ports'], shared_pool_KiB=32,
                R4_tokens_per_second=baseline['tokens_per_second'],
                shared32B_tokens_per_second=old_row['tokens_per_second'],
                shared16B_tokens_per_second=new_row['tokens_per_second'],
                rate_change_vs_32B=new_row['tokens_per_second'] / old_row['tokens_per_second'] - 1,
                speedup_vs_R4=baseline['seconds'] / new_row['seconds']))
        report.update(summary=summaries, pool0_complete_RESULT_exact=True,
                      original32B_complete_RESULT_exact=True, passed=True)
        (out / 'summary.json').write_text(json.dumps(dict(scope=SCOPE, limitations=LIMITATIONS,
                   cases=summaries, native_full_model_tokens_per_second=None), indent=2) + '\n', encoding='utf8')
    except Exception as exc:
        report.update(error=str(exc), traceback=traceback.format_exc())
    report['output_sha256'] = {p.relative_to(out).as_posix(): sha(p) for p in out.rglob('*')
                              if p.is_file() and p != out / 'result.json'}
    save()
    print(json.dumps(dict(passed=report['passed'], result=str(out / 'result.json'))), flush=True)
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
