"""Collect actual mother RTL/gate activity and original-Lib/RC sampled power.

Finite peers exercise single/two-target/held-call programs. They do not model
Qwen execution or prove that the accepted two-target hardware controls nine
resident Block instances. No complete-chip energy is produced here.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(command, log):
    with log.open('wb') as stream:
        result = subprocess.run(list(map(str, command)), stdout=stream, stderr=subprocess.STDOUT)
    if result.returncode:
        raise RuntimeError('failed experiment; preserve '+str(log))


def functional(log):
    text = log.read_text()
    if 'PASS mother' not in text:
        raise ValueError('existing public-port assertions did not finish')
    row, = [json.loads(line[11:]) for line in text.splitlines() if line.startswith('FUNCTIONAL ')]
    return row


def main():
    p = argparse.ArgumentParser()
    for name in ('accepted', 'binaries', 'liberty', 'output'):
        p.add_argument(name, type=Path)
    p.add_argument('--power', action='store_true')
    a = p.parse_args()
    a.output.mkdir(exist_ok=False)
    manifest = json.loads((a.accepted/'manifest.json').read_text())
    for suffix in ('v', 'odb', 'sdc', 'spef'):
        name = 'physical/6_final.'+suffix
        if sha(a.accepted/name) != manifest['files_sha256'][name]:
            raise ValueError('accepted physical source drift')
    bank = a.accepted/'bank-dependency/s_sram_256x128_freepdk45_TT_1p1V_25C.lib'
    if sha(bank) != '47f8de1c22d27beb51982c73ab745e1f3f2b5a7819e53bcb6da73980ce077189':
        raise ValueError('original SRAM characterization drift')
    initials = [(1, 143), (2, 143), (2, 144)]
    cases = [('single', 16, 16, {}), ('two_parallel', 16, 32, {}),
             ('held_call', 4, 8, {'HOLD_TARGET': 0, 'HOLD_CYCLES': 180, 'DELAY1': 10})]
    rows = []
    for case, jobs, calls, parameters in cases:
        out = a.output/case
        out.mkdir()
        image = a.accepted/('gate/replay/'+case+'.mem')
        if sha(image) != manifest['files_sha256']['gate/replay/'+case+'.mem']:
            raise ValueError('accepted image drift')
        words = len(image.read_text().splitlines())
        records, power = {}, {}
        active_cycles = None
        for mode in ('active', 'idle'):
            previous = None
            for kind in ('rtl', 'gate'):
                for initial, seed in initials:
                    label = '%s-%s-%d-%d'%(kind, mode, initial, seed)
                    wave, log = out/(label+'.vcd'), out/(label+'.log')
                    args = {'IMAGE': image, 'WORDS': words, 'RUNS': jobs, 'CALLS': calls, **parameters}
                    if mode == 'idle':
                        args['ACTIVITY_IDLE_CYCLES'] = active_cycles
                    command = [a.binaries/kind/'obj/Vtb_mother', wave,
                        '+verilator+rand+reset+'+str(initial), '+verilator+seed+'+str(seed)]
                    command += ['+'+name+'='+str(value) for name, value in args.items()]
                    run(command, log)
                    row = functional(log)
                    if previous is not None and row != previous:
                        raise ValueError('RTL/gate/initialization timing or transaction mismatch')
                    previous = row
                    if mode == 'active':
                        if (row['calls'], row['results']) != (calls, jobs):
                            raise ValueError('incomplete mother jobs')
                        active_cycles = row['timing']['window_cycles']
                    elif (row['calls'], row['results']) != (0, 0) or row['timing']['window_cycles'] != active_cycles:
                        raise ValueError('idle fixture performs work or has a different clock window')
                    expected = active_cycles*10000/3
                    if abs(row['timing']['window_ps']-expected) > 1:
                        raise ValueError('actual window differs from rational300MHz clock')
                    receipt = out/(label+'.json')
                    receipt.write_text(json.dumps(row, indent=2)+'\n')
                    records[label] = {'functional': row, 'waveform_sha256': sha(wave), 'log_sha256': sha(log)}
                    if a.power and kind == 'gate':
                        target = out/('power-'+label)
                        command = [sys.executable, '-X', 'faulthandler', Path(__file__).with_name('analyze_activity.py'),
                            a.accepted/'physical', a.liberty, wave, receipt, target, '--cores', '1',
                            '--scope', 'bench/tb_mother/dut', '--extra-lib', bank, '--escape-sta-backslashes',
                            '--audit-unannotated-diodes',
                            '--sample-label', 'accepted two-target mother runtime']
                        run(command, out/('analysis-'+label+'.log'))
                        power[label] = json.loads((target/'receipt.json').read_text())
            if mode == 'active':
                duration = previous['timing']['window_ps']
        increments = []
        if a.power:
            for initial, seed in initials:
                active = power['gate-active-%d-%d'%(initial, seed)]['power_w']['total']
                idle = power['gate-idle-%d-%d'%(initial, seed)]['power_w']['total']
                if active < idle:
                    raise ValueError('negative activity subtraction; do not clamp')
                increments.append({'initial': initial, 'seed': seed, 'idle_w': idle,
                    'incremental_per_job_j': (active-idle)*duration*1e-12/jobs})
        row = {'case': case, 'jobs': jobs, 'calls': calls, 'window_cycles': active_cycles,
            'window_ps': duration, 'records': records, 'power': power, 'sampled_increments': increments,
            'unannotated_pins_independently_classified': False,
            'complete_control_energy_qualified': False, 'system_timing_qualified': False}
        (out/'receipt.json').write_text(json.dumps(row, indent=2)+'\n')
        rows.append(row)
        print(json.dumps({'case': case, 'jobs': jobs, 'window_cycles': active_cycles, 'passed': True}), flush=True)
    result = {'scope': __doc__, 'passed': True, 'rows': rows,
        'accepted_manifest_sha256': sha(a.accepted/'manifest.json'),
        'binaries_sha256': {k: sha(a.binaries/k/'obj/Vtb_mother') for k in ('rtl', 'gate')},
        'sources_sha256': {n: sha(Path(__file__).with_name(n)) for n in
            ('mother_probe.py', 'mother_activity.py', 'mother_activity.cpp', 'analyze_activity.py')},
        'unannotated_pin_audit_still_required': a.power, 'full_model_numeric_qualified': False,
        'system_timing_qualified': False, 'total_energy_qualified': False}
    (a.output/'receipt.json').write_text(json.dumps(result, indent=2)+'\n')


if __name__ == '__main__':
    main()
