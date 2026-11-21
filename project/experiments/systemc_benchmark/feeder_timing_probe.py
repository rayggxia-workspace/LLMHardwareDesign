"""Compare clocked SystemC finite-FIFO timing with actual accepted RTL/gate events.

Parses pre-edge ready/valid, not post-edge values. Checks every packet and held
completion in all 32 repeated jobs. This is a feeder subsystem, not a complete
Qwen service or system time/energy qualification.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess


PORTS = ('clk', 'load_valid', 'load_ready', 'a_valid', 'a_ready', 'a_row', 'a_tile',
         'b_valid', 'b_ready', 'b_tile', 'b_half', 'done_valid', 'done_take')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def vcd_jobs(path):
    mapping, stack, current, previous, jobs = {}, [], {}, {}, []
    cycle, start, job, completed = 0, None, [], False
    def frame():
        nonlocal previous, cycle, start, job, completed
        if previous.get('clk') == 0 and current.get('clk') == 1:
            state = previous
            if set(state) != set(PORTS):
                raise ValueError('incomplete top-level feeder port state')
            if state['load_valid'] and state['load_ready']:
                if start is not None:
                    raise ValueError('overlapping serialized feeder jobs')
                start, job, completed = cycle, [], False
                job.append({'cycle': 0, 'kind': 'L', 'row': 0, 'tile': 0, 'half': 0})
            if start is not None:
                def event(kind, row=0, tile=0, half=0):
                    job.append({'cycle': cycle-start, 'kind': kind, 'row': row, 'tile': tile, 'half': half})
                if state['a_valid'] and state['a_ready']:
                    event('A', state['a_row'], state['a_tile'])
                if state['b_valid'] and state['b_ready']:
                    event('B', tile=state['b_tile'], half=state['b_half'])
                if state['done_valid'] and not completed:
                    event('D');completed = True
                if state['done_valid'] and state['done_take']:
                    event('T');jobs.append(job);start = None
            cycle += 1
        previous = dict(current)
    with path.open() as stream:
        for line in stream:
            fields = line.split()
            if fields[:1] == ['$scope']:
                stack.append(fields[2])
            elif fields[:1] == ['$upscope']:
                stack.pop()
            elif fields[:1] == ['$var']:
                full = '/'.join(stack+[fields[4]])
                if full.startswith('dut/') and full[4:] in PORTS:
                    mapping[fields[3]] = full[4:]
            elif line.startswith('#'):
                frame()
            elif line.startswith('b'):
                value, identifier = fields
                if identifier in mapping:
                    current[mapping[identifier]] = int(value[1:], 2)
            elif line[:1] in '01' and line[1:].strip() in mapping:
                current[mapping[line[1:].strip()]] = int(line[0])
    frame()
    if set(mapping.values()) != set(PORTS) or start is not None or not jobs:
        raise ValueError('missing ports or incomplete feeder transactions')
    return jobs


def main():
    p = argparse.ArgumentParser()
    for n in ('executable', 'binaries', 'operands', 'output'):
        p.add_argument(n, type=Path)
    a = p.parse_args()
    a.output.mkdir(exist_ok=False)
    cases = [('b1', 1, 4, 1, 1, 0, 0), ('b1-reuse', 1, 4, 1, 1, 1, 0),
             ('b1-stalled', 1, 4, 1, 1, 0, 1), ('b8', 8, 4, 1, 1, 0, 0),
             ('b8-reuse', 8, 4, 1, 1, 1, 0), ('b8-stalled', 8, 4, 1, 1, 0, 1)]
    rows = []
    for name, r, t, aw, bw, reuse, stall in cases:
        out = a.output/name
        out.mkdir()
        log = out/'systemc.log'
        with log.open('wb') as stream:
            result = subprocess.run(list(map(str, [a.executable, r, t, bw, reuse, stall])),
                                    stdout=stream, stderr=subprocess.STDOUT)
        if result.returncode:
            raise RuntimeError('architectural model failed; see '+str(log))
        model, = [json.loads(s[7:]) for s in log.read_text().splitlines() if s.startswith('RESULT ')]
        actual = {}
        for kind in ('rtl', 'gate'):
            vcd, receipt = out/(kind+'.vcd'), out/(kind+'.log')
            with receipt.open('wb') as stream:
                result = subprocess.run(list(map(str, [a.binaries/kind, a.operands, vcd,
                    'active', r, t, aw, bw, reuse, stall,
                    '+verilator+rand+reset+1', '+verilator+seed+143'])),
                    stdout=stream, stderr=subprocess.STDOUT)
            if result.returncode:
                raise RuntimeError('independent RTL array/packet test failed; see '+str(receipt))
            functional, = [json.loads(s[11:]) for s in receipt.read_text().splitlines() if s.startswith('FUNCTIONAL ')]
            jobs = vcd_jobs(vcd)
            if len(jobs) != 32 or any(j != model['events'] for j in jobs):
                (out/(kind+'-parsed-events.json')).write_text(json.dumps(jobs, indent=2)+'\n')
                raise ValueError('clocked SystemC packet/completion events differ from pre-edge '+kind+' trace')
            period = functional['timing']['feeder_period_cycles_with_done_hold3']
            if period != model['period_cycles_with_done_hold3']:
                raise ValueError('SystemC/RTL release periods differ')
            if model['makespan_ps'] != (period*10000+2)//3:
                raise ValueError('SystemC rational-clock accounting drift')
            actual[kind] = {'VCD_sha256': sha(vcd), 'jobs': len(jobs),
                            'functional': functional, 'all_pre_edge_events_equal': True}
        row = {'case': name, 'SystemC': model, 'observed': actual,
               'wide_reads_independent_formula': t*((r+3)//4+(0 if reuse else (2 if bw else 1)))}
        if row['wide_reads_independent_formula'] != model['wide_memory_reads']:
            raise ValueError('wide read count differs from independent packet packing formula')
        rows.append(row)
        print(json.dumps({'case': name, 'period_cycles': model['period_cycles_with_done_hold3'],
                          'all_64_RTL_gate_jobs_events_equal': True}), flush=True)
    result = {'scope': __doc__, 'rows': rows, 'passed': True,
        'executable_sha256': sha(a.executable), 'binary_sha256': {k: sha(a.binaries/k) for k in ('rtl', 'gate')},
        'driver_sha256': sha(Path(__file__)),
        'systemc_source_sha256': sha(Path(__file__).with_name('systemc_feeder.cpp')),
        'operand_sha256': sha(a.operands), 'clock_hz': 300000000,
        'system_timing_qualified': False, 'full_model_numeric_qualified': False, 'total_energy_qualified': False}
    (a.output/'receipt.json').write_text(json.dumps(result, indent=2)+'\n')


if __name__ == '__main__':
    main()
