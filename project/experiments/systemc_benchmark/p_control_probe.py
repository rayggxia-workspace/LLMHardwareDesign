"""Sample one accepted P_64 program and its matched deployed idle window.

Parent Liberty views are timing abstracts for the independent M/G/S leaves.
The parent power report therefore does NOT include their internal power.
This program is not a general LC service coefficient or Qwen execution.
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
        subprocess.run(list(map(str, command)), stdout=stream,
                       stderr=subprocess.STDOUT, check=True)


def main():
    p = argparse.ArgumentParser()
    for name in ('accepted', 'accepted_receipt', 'binaries', 'liberty', 'output'):
        p.add_argument(name, type=Path)
    p.add_argument('--power', action='store_true')
    a = p.parse_args()
    # Validate every selected accepted input, not just the parent netlist.
    receipt = json.loads(a.accepted_receipt.read_text())
    if receipt['archive_sha256'] != '13545e6ee575512edac07aebe553bf5d6c8666ccec3b040afde581cd4f35c390':
        raise ValueError('unexpected accepted P64 archive')
    for name, row in receipt['selected_files'].items():
        if sha(a.accepted/name) != row['sha256']:
            raise ValueError('accepted input drift: '+name)
    generation = json.loads((a.binaries/'sources/generation.json').read_text())
    if generation['accepted_receipt_sha256'] != sha(a.accepted_receipt):
        raise ValueError('instrumented fixture belongs to another acceptance')
    a.output.mkdir(exist_ok=False)
    orig = a.accepted/'gate/normal'
    images = {name: orig/('results/normal/'+name+'.mem')
              for name in ('mother', 'local0', 'local1')}
    lengths = {name: len(path.read_text().splitlines()) for name, path in images.items()}
    records, power = {}, {}
    initials = ((1, 143), (2, 143), (2, 144))
    previous_active = previous_idle = None
    for mode in ('active', 'idle'):
        for kind in ('rtl', 'gate'):
            for initial, seed in initials:
                label = '%s-%s-%d-%d'%(kind, mode, initial, seed)
                wave, log = a.output/(label+'.vcd'), a.output/(label+'.log')
                command = [a.binaries/kind/'obj/Vtb_native_pair', wave,
                    '+MOTHER='+str(images['mother']), '+MWORDS='+str(lengths['mother']),
                    '+LOCAL0='+str(images['local0']), '+WORDS0='+str(lengths['local0']),
                    '+LOCAL1='+str(images['local1']), '+WORDS1='+str(lengths['local1']),
                    '+STALL=0', '+FAULT=0', '+RESET_TRIAL=0',
                    '+verilator+rand+reset+'+str(initial), '+verilator+seed+'+str(seed)]
                if mode == 'idle':
                    command.append('+ACTIVITY_IDLE_CYCLES='+str(previous_active['timing']['window_cycles']))
                run(command, log)
                text = log.read_text()
                marker = 'PASS native kind=3' if mode == 'active' else 'PASS native deployed idle'
                if marker not in text:
                    raise ValueError('original assertions did not finish: '+label)
                row, = [json.loads(line[11:]) for line in text.splitlines()
                        if line.startswith('FUNCTIONAL ')]
                previous = previous_active if mode == 'active' else previous_idle
                if previous is not None and row != previous:
                    raise ValueError('RTL/gate/initialization timing differs: '+label)
                if mode == 'active':
                    previous_active = row
                else:
                    previous_idle = row
                    if row['timing'] != previous_active['timing']:
                        raise ValueError('idle clock window differs from active')
                if abs(row['timing']['window_ps'] - row['timing']['window_cycles']*10000/3) > 1:
                    raise ValueError('runtime window differs from rational300MHz clock')
                target = a.output/(label+'.json')
                target.write_text(json.dumps(row, indent=2)+'\n')
                records[label] = {'functional': row, 'waveform_sha256': sha(wave), 'log_sha256': sha(log)}
                if a.power and kind == 'gate':
                    out = a.output/('power-'+label)
                    command = [sys.executable, '-X', 'faulthandler',
                        Path(__file__).with_name('analyze_activity.py'), a.accepted/'native',
                        a.liberty, wave, target, out, '--cores', '1',
                        '--scope', 'bench/tb_native_pair/local_block[0]/endpoint/programmable_p/implementation',
                        '--escape-sta-backslashes', '--audit-unannotated-diodes',
                        '--sample-label', 'accepted P64 parent only; M/G/S internals excluded']
                    for macro in ('multiply', 'gate', 'store'):
                        command += ['--extra-lib', a.accepted/('native/views/'+macro+'.lib')]
                    run(command, a.output/('analysis-'+label+'.log'))
                    power[label] = json.loads((out/'receipt.json').read_text())
    increments = []
    if a.power:
        duration = previous_active['timing']['window_ps']*1e-12
        for initial, seed in initials:
            active = power['gate-active-%d-%d'%(initial, seed)]['power_w']['total']
            idle = power['gate-idle-%d-%d'%(initial, seed)]['power_w']['total']
            if active < idle:
                raise ValueError('negative parent activity subtraction; do not clamp')
            increments.append({'initial': initial, 'seed': seed, 'idle_w': idle,
                               'incremental_per_fixture_j': (active-idle)*duration})
    result = {'scope': __doc__, 'passed': True, 'records': records, 'power': power,
        'sampled_increments': increments, 'generation': generation,
        'binaries_sha256': {kind: sha(a.binaries/kind/'obj/Vtb_native_pair') for kind in ('rtl', 'gate')},
        'images_sha256': {name: sha(path) for name, path in images.items()},
        'sources_sha256': {name: sha(Path(__file__).with_name(name)) for name in
            ('p_control_probe.py', 'p_control_activity.py', 'p_control_activity.cpp', 'analyze_activity.py')},
        'leaf_internal_energy_included': False, 'full_model_timing_qualified': False,
        'total_energy_qualified': False}
    (a.output/'receipt.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({'passed': True, 'window': previous_active['timing'],
                      'parent_power_samples': len(increments)}))


if __name__ == '__main__':
    main()
