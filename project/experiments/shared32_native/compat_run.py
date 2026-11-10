"""Slurm-only paired original/new default-RTL regression with exact event logs."""
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import signal
import subprocess
import sys
import time
import traceback

from compat_generate import BASELINE, BENCHES, generate, sha

HERE = Path(__file__).resolve().parent
VERILATOR = Path('/public/home/yuzelu/opt/eda/verilator-5-042-repro02/bin/verilator')
BANK = Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-155/bank-views-011/generation/bank/s_sram_256x128_freepdk45.v')
BANK_SHA = '6c1c1ca9d183ab7c4c74df056c9730cf352d165301546126e29b644a45ef9de7'
SOURCES = [
    'project/rtl/block_local_s/block_local_s_arbiter.sv',
    'project/rtl/block_local_s/popt_s_policy_arbiter.sv',
    'project/rtl/s_sram/block_feed_s16k_sram.sv',
    'project/rtl/s_sram/block_feed_s16k_bank_rw.sv',
    'project/rtl/s_sram/local_s_p.sv',
    'project/rtl/block_feed_v1/block_feed_loader.sv',
    'project/rtl/block_v2/block_v2_m.sv',
    'project/rtl/block_v2/block_v2_m_context.sv',
    'project/rtl/block_v2/block_v2_g.sv',
    *['project/rtl/pu_leaf_base/'+name+'.sv' for name in
      ('pu_p_group', 'pu_p_store_control', 'pj_feed_hold', 'pj_mem_port', 'pj_sram_client')],
]
CASES = [
    ('group-default-s2', 'group', 'tb_popt_group', dict(OPT=0, BANK_RW=0, SEGMENTS=2), 'PASS P_GROUP native S'),
    ('original-P-program', 'program', 'tb_pu_p_group', {}, 'PASS P16 feed'),
    ('local-h0', 'local', 'tb_popt_local', dict(BANK_RW=0, REUSE_A=0, HOLD_CYCLES=0), 'POPT_LOCAL_PASS'),
    ('local-h32', 'local', 'tb_popt_local', dict(BANK_RW=0, REUSE_A=0, HOLD_CYCLES=32), 'POPT_LOCAL_PASS'),
]
SEEDS = ((1, 143), (2, 143), (2, 144))
RECEIPT_PREFIXES = ('COMPAT_EVENT ', 'METRIC ', 'P_GROUP_OVERLAP ', 'POPT_LOCAL_', 'PASS ')
STUDY_PATH = 'project/experiments/shared32_native/'
REQUIRED_CODE = set(SOURCES) | set(BENCHES.values()) | {
    'project/rtl/block_v2/block_v2_g_tables.svh',
    'project/rtl/s_sram/block_feed_s16k_1r1w.sv',
    *[STUDY_PATH+name for name in ('compat_generate.py', 'compat_run.py',
                                 'compat_cold_local.sv', 'compat_job.sh',
                                 'compat_baseline/source.json',
                                 'compat_baseline/local_s_p.sv',
                                 'compat_baseline/block_feed_loader.sv',
                                 'compat_baseline/pu_p_group.sv')],
}


def pin_warnings(text):
    """Normalize locations only; retain the complete actual diagnostic text."""
    result = []
    for line in text.splitlines():
        if re.match(r'%(Warning|Error)-(PINMISSING|PINNOTFOUND):', line):
            result.append(re.sub(r': .*?:\d+:\d+:\s*', ': ', line, count=1))
    return result


def ensure(condition, message):
    if not condition:
        raise ValueError(message)


def receipt(text):
    lines = [line for line in text.splitlines() if line.startswith(RECEIPT_PREFIXES)]
    ensure(any(line.startswith('COMPAT_EVENT ') for line in lines), 'missing observed events')
    return '\n'.join(lines)+'\n'


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--root', type=Path, required=True)
    a = p.parse_args()
    root = a.root.resolve()
    repo, out = root/'source', root/'results'
    workers = int(os.environ.get('SLURM_CPUS_PER_TASK', '0'))
    ensure(bool(os.environ.get('SLURM_JOB_ID')) and 1 <= workers <= 4, 'Slurm allocation of 1..4 CPUs required')
    manifest = json.loads((root/'inputs.json').read_bytes())
    ensure(re.fullmatch('[0-9a-f]{40}', manifest.get('source_commit', '')) is not None, 'real commit absent')
    ensure(REQUIRED_CODE <= set(manifest.get('code_sha256', {})),
           'required code absent from manifest: '+repr(sorted(REQUIRED_CODE-set(manifest.get('code_sha256', {})))))
    for field, base in (('code_sha256', repo), ('input_sha256', root)):
        for name, expected in manifest.get(field, {}).items():
            ensure(sha(base/name) == expected, 'deployment drift '+name)
    ensure(bool(manifest.get('code_sha256')), 'empty code deployment manifest')
    ensure(sha(BANK) == BANK_SHA, 'actual SRAM macro identity drift')
    out.mkdir(exist_ok=False)
    result = dict(passed=False, source_commit=manifest['source_commit'],
        manifest_sha256=sha(root/'inputs.json'), bank_sha256=sha(BANK),
        slurm_job_id=os.environ['SLURM_JOB_ID'], commands=[], comparisons=[], cold_reset_runs=[], pin_diagnostic_checks=[],
        required_code_sha256={name: manifest['code_sha256'][name] for name in sorted(REQUIRED_CODE)},
        allocation_receipt_sha256=sha(root/'allocation.txt') if (root/'allocation.txt').exists() else None,
        tools_receipt_sha256=sha(root/'tools.sha256') if (root/'tools.sha256').exists() else None,
        versions=dict(python=platform.python_version()),
        scope='default production RTL numerical/cycle compatibility only; no full-model token/s or physical qualification')

    def save():
        (out/'result.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf8')

    def execute(command, name, timeout=60):
        command = list(map(str, command))
        started = time.monotonic()
        process = subprocess.Popen(command, cwd=repo, stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT, start_new_session=True)
        timed_out = False
        try:
            output, _ = process.communicate(timeout=timeout)
        except subprocess.TimeoutExpired as expired:
            timed_out = True
            # Compilers and simulation executables can leave child processes;
            # terminate the complete newly created process group, not one PID.
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            try:
                output, _ = process.communicate(timeout=10)
            except subprocess.TimeoutExpired as still_open:
                output = still_open.output or expired.output or b''
                if process.stdout is not None:
                    process.stdout.close()
                try:
                    process.kill()
                    process.wait(timeout=5)
                except (ProcessLookupError, subprocess.TimeoutExpired):
                    pass
            output += ('\nCOMPAT_TIMEOUT seconds='+str(timeout)+' process_group='+str(process.pid)+' killed\n').encode()
        target = out/name
        target.write_bytes(output)
        result['commands'].append(dict(command=command, exit_code=process.returncode, timed_out=timed_out,
            timeout_seconds=timeout, process_group=process.pid,
            elapsed_seconds=time.monotonic()-started, log=name, sha256=sha(target)))
        save()
        if timed_out:
            raise RuntimeError(name+' exceeded '+str(timeout)+' seconds; process group killed; log preserved')
        if process.returncode:
            raise RuntimeError(name+' failed '+str(process.returncode)+'\n'+output.decode(errors='replace')[-3000:])
        return output.decode(errors='replace')

    try:
        result['versions']['verilator'] = execute([VERILATOR, '--version'], 'verilator-version.log').strip()
        result['versions']['gcc'] = execute(['g++', '--version'], 'gcc-version.log').splitlines()[0]
        generated = out/'generated'
        info = generate(repo, generated)
        result['generation'] = info
        baseline_files = info['baseline']['files']
        # These unchanged dependencies are locked by the deployment manifest;
        # only the three explicitly recorded modules vary in the paired builds.
        result['common_source_sha256'] = {name: sha(repo/name) for name in SOURCES if name not in baseline_files}

        def build(label, top, bench, params, original=False, local_only=False):
            sources = SOURCES if not local_only else [name for name in SOURCES if
                '/s_sram/' in name or name.endswith('/block_feed_loader.sv')]
            paths = [BASELINE/baseline_files[name]['snapshot'] if original and name in baseline_files else repo/name
                     for name in sources]
            if not original:
                paths.append(repo/'project/rtl/s_sram/block_feed_s16k_1r1w.sv')
            obj = out/('obj-'+label)
            # Preserve the existing p_native_opt legacy warning policy. New
            # module strict lint belongs to the shared32 native primary run.
            cmd = [VERILATOR, '--binary', '--timing', '--assert', '--timescale', '1ns/1ps',
                   '-Wno-fatal', '--x-initial', 'unique', '--x-assign', 'unique', '-j', workers,
                   '-I'+str(repo/'project/rtl/block_v2'), '--top-module', top, '--Mdir', obj]
            cmd += ['-G'+name+'='+str(value) for name, value in params.items()]
            cmd += [bench, *paths, BANK]
            text = execute(cmd, label+'-build.log', timeout=240)
            return obj/('V'+top), pin_warnings(text)

        for label, kind, top, params, marker in CASES:
            variants = {}
            original_pins = []
            for original in (True, False):
                variant = 'original' if original else 'candidate'
                binary, warnings = build(label+'-'+variant, top, generated/(kind+'-'+variant+'.sv'), params,
                                         original, kind == 'local')
                if original:
                    original_pins = warnings
                else:
                    extra_pins = Counter(warnings)-Counter(original_pins)
                    result['pin_diagnostic_checks'].append(dict(label=label, original=original_pins,
                        candidate=warnings, new_candidate_diagnostics=dict(extra_pins)))
                    ensure(not extra_pins, label+' introduced missing/unknown ports: '+repr(dict(extra_pins)))
                outputs = []
                for mode, seed in SEEDS:
                    log = label+'-'+variant+'-'+str(mode)+'-'+str(seed)+'.log'
                    text = execute([binary, '+verilator+rand+reset+'+str(mode), '+verilator+seed+'+str(seed)], log)
                    ensure(marker in text, 'legacy numerical/assertion receipt missing: '+log)
                    normalized = receipt(text)
                    target = out/(log+'.events')
                    target.write_text(normalized, encoding='utf8')
                    outputs.append(dict(mode=mode, seed=seed, text=normalized, event_sha256=sha(target), log=log))
                variants[variant] = outputs
            for old, new in zip(variants['original'], variants['candidate']):
                ensure(old['text'] == new['text'], label+' differs in numerical values, cycles, or original receipts')
                result['comparisons'].append(dict(label=label, mode=old['mode'], seed=old['seed'],
                    exact_events_and_original_receipts=True, lines=len(old['text'].splitlines()),
                    sha256=old['event_sha256'], original_log=old['log'], candidate_log=new['log']))
            save()
        binary, warnings = build('cold-local', 'compat_cold_local', HERE/'compat_cold_local.sv', {}, local_only=True)
        result['pin_diagnostic_checks'].append(dict(label='cold-local', candidate=warnings))
        ensure(not warnings, 'cold-local has missing/unknown ports: '+repr(warnings))
        for mode, seed in SEEDS:
            log = 'cold-local-'+str(mode)+'-'+str(seed)+'.log'
            text = execute([binary, '+verilator+rand+reset+'+str(mode), '+verilator+seed+'+str(seed)], log)
            marker = 'COMPAT_COLD_PASS cold_pending=1 cold_held=1 warm_preserved=1 completed_jobs=3 logical_bytes=16384 physical_bytes=32768'
            ensure(marker in text, 'cold-reset branch evidence missing')
            result['cold_reset_runs'].append(dict(mode=mode, seed=seed, log=log, sha256=sha(out/log)))
        ensure(len(result['comparisons']) == 12 and len(result['cold_reset_runs']) == 3, 'incomplete compatibility closure')
        result['passed'] = True
        print('SHARED32_COMPAT_PASS exact_default_pairs=12 cold_reset_runs=3', flush=True)
    except Exception as error:
        result['error'] = repr(error)
        result['traceback'] = traceback.format_exc()
        raise
    finally:
        save()


if __name__ == '__main__':
    main()
