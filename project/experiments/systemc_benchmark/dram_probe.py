"""Check a SystemC/DRAMsim3 bridge against direct replay and audited units.

Synthetic transport evidence only. The upstream DDR4 parameter set is a model,
not a selected board/controller or measured memory subsystem. In this pinned
DRAMsim3, total_energy is V*mA*cycles despite its pJ label: multiply by tCK_ns
and 1e-12 for J. Controller/PHY/termination/VPP remain outside this model.
"""
import argparse
import configparser
import hashlib
import json
from pathlib import Path
import subprocess


PIN = '29817593b3389f1337235d63cac515024ab8fd6e'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def energy(config, stats):
    """Independently reconstruct command/background current-time accounting."""
    f = lambda section, key: config.getfloat(section, key)
    devices = f('system', 'bus_width') / f('dram_structure', 'device_width')
    voltage, active, idle = [f('power', n) for n in ('VDD', 'IDD3N', 'IDD2N')]
    ras, rp, rfc = [f('timing', n) for n in ('tRAS', 'tRP', 'tRFC')]
    burst = f('dram_structure', 'BL')/2
    period = f('timing', 'tCK')
    units = 0.
    for row in stats.values():
        if row['num_refb_cmds'] or row['num_srefe_cmds'] or row['num_srefx_cmds']:
            raise ValueError('this independent audit only covers ordinary rank refresh')
        value = voltage * devices * (
            (f('power', 'IDD0')*(ras+rp)-active*ras-idle*rp)*row['num_act_cmds'] +
            (f('power', 'IDD4R')-active)*burst*row['num_read_cmds'] +
            (f('power', 'IDD4W')-active)*burst*row['num_write_cmds'] +
            (f('power', 'IDD5AB')-active)*rfc*row['num_ref_cmds'] +
            active*sum(row['rank_active_cycles'].values()) +
            idle*sum(row['all_bank_idle_cycles'].values()))
        if abs(value-row['total_energy']) > max(1e-7, abs(value)*1e-12):
            raise ValueError('independent DRAM energy reconstruction differs')
        if abs(value/row['num_cycles']-row['average_power']) > 1e-8:
            raise ValueError('DRAM mean-power unit reconstruction differs')
        units += value
    return {'joules': units*period*1e-12, 'raw_V_mA_cycles': units,
            'tCK_ns': period, 'source_pJ_label_requires_tCK_correction': True,
            'scope': 'modeled DRAM IDD rails only; not controller/PHY/board energy'}


def main():
    p = argparse.ArgumentParser()
    p.add_argument('executable', type=Path)
    p.add_argument('dramsim3_source', type=Path)
    p.add_argument('output', type=Path)
    a = p.parse_args()
    commit = subprocess.check_output(['git', '-C', str(a.dramsim3_source),
                                     'rev-parse', 'HEAD']).decode().strip()
    if commit != PIN:
        raise ValueError('DRAMsim3 source version differs from unit audit')
    config_path = a.dramsim3_source/'configs/DDR4_8Gb_x8_3200.ini'
    a.output.mkdir(exist_ok=False)
    configurations = []
    for label, multiplier in [('native', 1), ('unified-queue-candidate', 1),
                              ('unit-scaling-only', 2)]:
        c = configparser.ConfigParser()
        c.optionxform = str
        c.read(str(config_path))
        if multiplier != 1:
            c['timing']['tCK'] = str(c.getfloat('timing', 'tCK')*multiplier)
        if label == 'unified-queue-candidate':
            c['system']['unified_queue'] = 'true'
        path = a.output/(label+'.ini')
        with path.open('w') as f:
            c.write(f)
        configurations.append((label, c, path))
    idle, read = [], [(i, i*64, 0, 0, -1) for i in range(96)]
    write = [(i, i*64, 1, 0, -1) for i in range(96)]
    mixed = [(i, i*64, 0, 0, -1) for i in range(64)] + [
        (i+64, (i+64)*64, 1, 0, i) for i in range(64)]
    cases = [('idle', idle, 1000), ('read-burst', read, 20000),
             ('write-burst', write, 20000), ('read-to-write', mixed, 20000)]
    rows = []
    for label, c, config in configurations:
        for name, trace, ticks in cases:
            if label == 'unit-scaling-only' and name != 'idle':
                continue
            if label == 'unified-queue-candidate' and name != 'read-to-write':
                continue
            root = a.output/(label+'-'+name)
            root.mkdir()
            source = root/'input.tsv'
            source.write_text(''.join('\t'.join(map(str, r))+'\n' for r in trace))
            results, statistics = [], []
            for engine in ('sc', 'direct'):
                out = root/engine
                out.mkdir()
                log = root/(engine+'.log')
                command = [str(a.executable), engine, str(config), str(out),
                    str(source if engine == 'sc' else root/'sc/accepted.tsv'), str(ticks)]
                with log.open('w') as f:
                    run = subprocess.run(command, stdout=f, stderr=subprocess.STDOUT)
                if run.returncode:
                    raise ValueError('bridge run failed; see '+str(log))
                result, = [json.loads(line[7:]) for line in log.read_text().splitlines()
                           if line.startswith('RESULT ')]
                results.append(result)
                statistics.append(json.loads((out/'dramsim3.json').read_text()))
            if results[0]['requests'] != results[1]['requests'] or statistics[0] != statistics[1]:
                raise ValueError('SystemC callbacks/counters differ from accepted-input direct replay')
            if not results[0]['callbacks_complete'] or any(
                    q['callback_tick'] > ticks for q in results[0]['requests']):
                raise ValueError('incomplete callback window')
            stats = statistics[0]
            reads = sum(s['num_read_cmds'] for s in stats.values())
            writes = sum(s['num_write_cmds'] for s in stats.values())
            expected_reads, expected_writes = sum(1-r[2] for r in trace), sum(r[2] for r in trace)
            drained = (reads, writes) == (expected_reads, expected_writes)
            stock_tail_example = label == 'native' and name == 'read-to-write'
            if stock_tail_example:
                # Preserve the original strict failure as a counterexample:
                # every callback has returned, but the separated queue leaves
                # a small tail below its next write-draining threshold.
                if reads != expected_reads or not 0 < expected_writes-writes <= 8:
                    raise ValueError('stock write-tail counterexample changed')
            elif not drained:
                raise ValueError('write callbacks did not prove physical command drain')
            if trace and not results[0]['queue_retry_events']:
                raise ValueError('burst fixture did not exercise queue backpressure')
            for request in results[0]['requests']:
                after = trace[request['id']][4]
                if after >= 0 and request['submitted_tick'] < results[0]['requests'][after]['callback_tick']:
                    raise ValueError('request issued before dependency completion')
            energies = energy(c, stats)
            if not trace:
                # Default 16GiB channel contains two 8GiB ranks, eight x8 devices/rank.
                # This 1000-cycle interval precedes the first scheduled refresh.
                expected = ticks*2*8*1.2*37
                if energies['raw_V_mA_cycles'] != expected:
                    raise ValueError('idle IDD accounting differs from independent two-rank formula')
            rows.append({'configuration': label, 'fixture': name, 'memory_cycles': ticks,
                'window_ps': results[0]['window_ps'], 'request_count': len(trace),
                'queue_retry_events': results[0]['queue_retry_events'], 'read_commands': reads,
                'write_commands': writes, 'energy': energies,
                'physical_commands_drained': drained,
                'buffered_tail_writes': expected_writes-writes,
                'stock_tail_counterexample_reproduced': stock_tail_example,
                'window_energy_includes_all_requested_writes': drained,
                'direct_callback_and_full_stats_equal': True,
                'longest_callback_ticks': max((q['callback_tick']-q['submitted_tick']
                                              for q in results[0]['requests']), default=0)})
            print(json.dumps(rows[-1]), flush=True)
    if rows[-1]['energy']['joules'] != 2*rows[0]['energy']['joules']:
        raise ValueError('tCK unit-scaling check failed')
    files = ['src/configuration.cc', 'src/controller.cc', 'src/simple_stats.cc',
             'src/dram_system.cc', 'src/memory_system.h', 'configs/DDR4_8Gb_x8_3200.ini']
    receipt = {'rows': rows, 'dramsim3_commit': commit,
        'sources_sha256': {n: sha(a.dramsim3_source/n) for n in files},
        'driver_sha256': sha(Path(__file__)), 'executable_sha256': sha(a.executable),
        'systemc_source_sha256': sha(Path(__file__).with_name('systemc_dram.cpp')),
        'passed': True, 'system_timing_qualified': False, 'total_energy_qualified': False,
        'limitations': ['synthetic queue/dependency/clock bridge only, not full workload',
            'native upstream DDR4 model, no selected hardware/controller qualification',
            'unit-scaling-only config is a unit test, never a physical timing candidate',
            'no controller/PHY/termination/VPP or board overhead energy',
            'write callback means buffered acceptance; physical command counts independently checked']}
    (a.output/'receipt.json').write_text(json.dumps(receipt, indent=2)+'\n')


if __name__ == '__main__':
    main()
