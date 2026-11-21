"""Compare independent clocked SystemC mother events to accepted RTL/gate VCD.

Only deployed CALL/WAIT/MOVI/END compact runtime is modeled. PM bank latency,
finite terminal credits, serial result arbitration and host result hold are real
states; finite peers remain fixtures, not Qwen execution. No total energy claim.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess


PORTS = ('clk_i', 'start_valid_i', 'start_ready_o', 'task_valid_o',
         'task_ready_i', 'task_target_o', 'task_packet_o', 'return_valid_i',
         'return_ready_o', 'return_packet_i', 'result_valid_o', 'result_ready_i',
         'trace_retire_o', 'trace_pc_o', 'trace_opcode_o')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def control_events(path):
    mapping, stack, current, previous, events = {}, [], {}, {}, []
    cycle, started, seen_result = 0, False, False
    def frame():
        nonlocal previous, cycle, started, seen_result
        if previous.get('clk_i') == 0 and current.get('clk_i') == 1:
            if set(previous) != set(PORTS):
                raise ValueError('missing mother public-port state')
            s = previous
            def event(kind, value=0, detail=0):
                events.append({'cycle': cycle, 'kind': kind, 'value': value, 'detail': detail})
            if s['start_valid_i'] and s['start_ready_o']:
                started, seen_result = True, False
                event('S')
            if s['task_valid_o'] and s['task_ready_i']:
                if (s['task_packet_o'] >> 16) & 255:
                    raise ValueError('CANCEL is outside this timing model')
                event('C', s['task_target_o'], (s['task_packet_o'] >> 136) & 255)
                events[-1]['arguments'] = [(s['task_packet_o'] >> (256+32*i)) & 0xffffffff for i in range(8)]
            if s['return_valid_i'] and s['return_ready_o']:
                if (s['return_packet_i'] >> 16) & 255 != 2:
                    raise ValueError('READY/error return is outside this timing model')
                event('R', (s['return_packet_i'] >> 24) & 255)
            if s['result_valid_o'] and not seen_result:
                event('D'); seen_result = True
            if s['result_valid_o'] and s['result_ready_i']:
                event('A')
            if s['trace_retire_o']:
                event('I', s['trace_pc_o'], s['trace_opcode_o'])
            cycle += 1
        previous = dict(current)
    with path.open() as stream:
        for line in stream:
            fields = line.split()
            if fields[:1] == ['$scope']:
                stack.append(fields[2])
            elif fields[:1] == ['$upscope']:
                stack.pop()
            elif fields[:1] == ['$var'] and stack == ['bench', 'tb_mother'] and fields[4] in PORTS:
                mapping.setdefault(fields[3], []).append(fields[4])
            elif line.startswith('#'):
                frame()
            elif line.startswith('b') and fields[1] in mapping:
                value = int(fields[0][1:], 2)
                current.update((n, value) for n in mapping[fields[1]])
            elif line[:1] in '01' and line[1:].strip() in mapping:
                current.update((n, int(line[0])) for n in mapping[line[1:].strip()])
    frame()
    if set(n for names in mapping.values() for n in names) != set(PORTS) or not started:
        raise ValueError('missing mother runtime ports or START')
    return events, cycle


def main():
    p = argparse.ArgumentParser()
    for name in ('executable', 'activity', 'accepted', 'output'):
        p.add_argument(name, type=Path)
    p.add_argument('--binaries', type=Path,
        help='also run accepted RTL/gate on MOVI and simultaneous terminal-return fixtures')
    a = p.parse_args()
    a.output.mkdir(exist_ok=False)
    cases = [('single', 'single', 16, 1, 20, 24, -1, 0),
             ('two_parallel', 'two_parallel', 16, 2, 20, 24, -1, 0),
             ('held_call', 'held_call', 4, 2, 20, 10, 0, 180)]
    if a.binaries:
        cases += [('movi', 'movi', 16, 1, 20, 24, -1, 0),
                  ('simultaneous_returns', 'two_parallel', 16, 2, 13, 20, -1, 0)]
    rows = []
    for name, image_name, jobs, calls, d0, d1, ht, hc in cases:
        image = a.accepted/('gate/replay/'+image_name+'.mem')
        log = a.output/(name+'-systemc.log')
        with log.open('wb') as stream:
            subprocess.run(list(map(str, [a.executable, image, jobs, d0, d1, ht, hc])),
                           stdout=stream, stderr=subprocess.STDOUT, check=True)
        model, = [json.loads(s[7:]) for s in log.read_text().splitlines() if s.startswith('RESULT ')]
        checks = []
        for kind in ('rtl', 'gate'):
            for init, seed in ((1, 143), (2, 143), (2, 144)):
                label = '%s-active-%d-%d' % (kind, init, seed)
                source = a.activity/name
                if name in ('movi', 'simultaneous_returns'):
                    source = a.output/name
                    source.mkdir(exist_ok=True)
                    wave, binary_log = source/(label+'.vcd'), source/(label+'.log')
                    args = [a.binaries/kind/'obj/Vtb_mother', wave,
                        '+verilator+rand+reset+'+str(init), '+verilator+seed+'+str(seed),
                        '+IMAGE='+str(image), '+WORDS='+str(len(image.read_text().splitlines())),
                        '+RUNS='+str(jobs), '+CALLS='+str(jobs*calls),
                        '+DELAY0='+str(d0), '+DELAY1='+str(d1)]
                    with binary_log.open('wb') as stream:
                        subprocess.run(list(map(str, args)), stdout=stream, stderr=subprocess.STDOUT, check=True)
                    text = binary_log.read_text()
                    if 'PASS mother' not in text:
                        raise ValueError('existing public-port assertions did not complete')
                    receipt, = [json.loads(s[11:]) for s in text.splitlines() if s.startswith('FUNCTIONAL ')]
                    (source/(label+'.json')).write_text(json.dumps(receipt, indent=2)+'\n')
                wave = source/(label+'.vcd')
                events, cycles = control_events(wave)
                receipt = json.loads((source/(label+'.json')).read_text())
                (a.output/(name+'-'+label+'-events.json')).write_text(json.dumps(events, indent=2)+'\n')
                if events != model['events'] or cycles != model['cycles'] or cycles != receipt['timing']['window_cycles']:
                    raise ValueError('independent SystemC/control events differ: '+name+' '+label)
                if abs(model['makespan_ps']-receipt['timing']['window_ps']) > 1:
                    raise ValueError('rational clock differs by more than1ps')
                checks.append({'label': label, 'VCD_sha256': sha(wave), 'all_events_equal': True})
        rows.append({'case': name, 'jobs': jobs, 'cycles': model['cycles'],
                     'model': model, 'checks': checks, 'image_sha256': sha(image)})
        print(json.dumps({'case': name, 'cycles': model['cycles'], 'all_six_event_checks_equal': True}), flush=True)
    result = {'scope': __doc__, 'passed': True, 'rows': rows, 'executable_sha256': sha(a.executable),
        'sources_sha256': {n: sha(Path(__file__).with_name(n)) for n in ('systemc_mother.cpp', 'mother_timing_probe.py')},
        'system_timing_qualified': False, 'total_energy_qualified': False,
        'configuration_fault_event_and_nine_target_coverage': False}
    (a.output/'receipt.json').write_text(json.dumps(result, indent=2)+'\n')


if __name__ == '__main__':
    main()
