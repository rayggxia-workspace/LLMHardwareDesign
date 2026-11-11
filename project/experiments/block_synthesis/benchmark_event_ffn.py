"""Replay #251 Qwen2.5-3B FFN K128 timing/custody against frozen RTL receipts.

The fixture serializes scope and K-tile admission. Measured provider waits are
part of those intervals. DDR byte counters are cross-checked against the scope
descriptors separately: the logs do not identify the individual issue/return
times of every weight beat. This replay does not predict a different provider.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tarfile
from time import perf_counter

from cover_frontier import search
from verify_cover_frontier import verify

NATIVE_REF = '9abd46f5cbb4534bcfc614571ccd6d402ad11882'
FIXTURE = 'project/experiments/native_s_calibration/fixtures/ffn-programmed-102604-102603.json'
PROFILES = ('K_PROFILE', 'FFN_PROFILE', 'DOWN_PROFILE', 'PROGRAM_PROFILE', 'DMA_PROFILE')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def load_case(archive, job, seed, mode, initial):
    frozen = json.loads(subprocess.check_output(['git', 'show', f'{NATIVE_REF}:{FIXTURE}']))
    profile, = [p for p in frozen['profiles'] if p['job'] == job]
    trial, = [t for t in profile['trials']
              if (t['seed'], t['mode'], t['initial']) == (seed, mode, initial)]
    with archive.open('rb') as source:
        require(hashlib.file_digest(source, 'sha256').hexdigest() == profile['receipt_sha256'],
                'RTL receipt archive differs from pinned SHA-256')
    prefix = f'seed-{seed}/'
    log = f'{prefix}mode-{mode}-initial-{initial}.log'
    rows, summary, oracle = [], {}, None
    with tarfile.open(archive, 'r|gz') as source:
        for member in source:
            if member.name == prefix + 'oracle.json':
                with source.extractfile(member) as file:
                    oracle = json.load(file)
            if member.name == log:
                with source.extractfile(member) as file:
                    for line in file:
                        tag = line.partition(b' ')[0].decode()
                        if tag not in PROFILES:
                            continue
                        fields = {name: int(value) for name, value in re.findall(
                            r'(\w+)=(-?\d+)', line.decode())}
                        if tag == 'K_PROFILE':
                            rows.append(fields)
                        else:
                            require(tag not in summary, 'duplicate terminal profile')
                            summary[tag] = fields
            if rows and oracle:
                break
    require(set(summary) == set(PROFILES[1:]) and oracle is not None, 'incomplete frozen receipt')
    require((summary['FFN_PROFILE']['cycles'], summary['DOWN_PROFILE']['cycles']) ==
            (trial['gate'], trial['down']), 'fixture phase cycles differ')
    for source, declared in (('PROGRAM_PROFILE', profile['program']), ('DMA_PROFILE', profile['dma'])):
        require(all(summary[source][k] == v for k, v in declared.items()), 'fixture counters differ')
    return rows, summary, oracle


def make_problem(rows, summary, oracle):
    scopes = oracle['first_descriptors']
    require(len(scopes) == 192 and oracle['mid_tiles'] == 86, 'unexpected Qwen FFN geometry')
    gate = summary['FFN_PROFILE']
    down = summary['DOWN_PROFILE']
    program = summary['PROGRAM_PROFILE']
    dma = summary['DMA_PROFILE']
    ddr_reads = sum(128 + s['records']*1088 for s in scopes)
    local_writes = sum(s['committed_words_per_way']*s['ways']*16 for s in scopes)
    require(ddr_reads == program['confirmed_reads'] == dma['backend_returns']*64
            == (gate['W64']+down['W64'])*64+192*128
            and local_writes == program['confirmed_writes'], 'scope traffic is not conserved')
    require(sum(s['records']*17 for s in scopes if s['phase'] == 'down') == down['W64'],
            'Down weight traffic differs')
    grouped = defaultdict(list)
    for row in rows:
        grouped[row['scope']].append(row)
    require(list(grouped) == list(range(1, 65)), 'scope order differs')

    sites = ('P0', 'P1', 'P2', 'U')
    ports = [p+'.S.port' for p in sites[:3]]
    compute = [p+'.M' for p in sites[:3]]
    resources = dict.fromkeys([*ports, *compute, 'U.S.port', 'COPY', 'outer'], 1)
    windows, values, services = {}, {}, {}
    active = [p+'.A' for p in sites[:3]]

    def window(name, site, word, count):
        windows[name] = {'site': site, 'offset': word*16, 'bytes': count*16}
        return name

    for i, p in enumerate(sites[:3]):
        window(active[i], p, 880, 16)
    initial_copies = {}
    for k in range(16):
        name = window(f'X32:{k}', 'U', 32*k, 32)
        values[name] = 512
        initial_copies[name] = name
        values[window(f'X16:{k}', 'U', 512+16*k, 16)] = 256
    for k in range(86):
        name = window(f'Mid:{k}', sites[k%3], 256+16*(k//3), 16)
        values[name] = 256

    def stage(name, ticks, uses, *, inputs=None, outputs=None):
        require(ticks > 0 and set(uses) <= resources.keys(), 'invalid measured stage')
        services[name] = {'ticks': ticks, 'claims': dict.fromkeys(uses, 1)}
        if name.endswith(':copy'):
            source, = inputs
            services[name]['copy_sites'] = [windows[source]['site'], [windows[w]['site'] for w in outputs]]
        return {'service': name, 'inputs': inputs or {}, 'outputs': outputs or {},
                'input_policy': 'resident'}

    tasks, live_out = [], []
    written_mid = 0
    for scope, trace in grouped.items():
        ident = f'scope-{scope:02d}'
        phase = int(scope >= 59)
        length = 86 if phase else 16
        require([(r['phase'], r['k']) for r in trace] == [(phase, k*128) for k in range(length)],
                'missing, duplicate or misordered K slice')
        first, last = (59, 64) if phase else (1, 58)
        measurement = down if phase else gate
        total = measurement['cycles']
        start_trace = grouped[first][0]['start']
        end_trace = grouped[last][-1]['released']
        stages = []
        for k, row in enumerate(trace):
            start, header, ack, released = (row[n] for n in ('start', 'header', 'copy', 'released'))
            require(start <= row['need'] <= row['quant'] <= header < ack <= row['proof'] < released,
                    'copy protocol timestamps differ')
            require(k == 0 or trace[k-1]['released'] == start, 'unexpected hole inside a scope')
            source = f'Mid:{k}' if phase else f'X16:{k}'
            quantizes = scope == 1
            stages.append(stage(f'{ident}:{k}:prepare', header-start,
                                ['U.S.port'] if quantizes else ['outer'],
                                inputs={f'X32:{k}': f'X32:{k}'} if quantizes else {},
                                outputs={source: source} if quantizes else {}))
            stages.append(stage(f'{ident}:{k}:copy', ack-header,
                                ['COPY', *ports, *([] if phase else ['U.S.port'])],
                                inputs={source: source}, outputs=dict.fromkeys(active, source)))
            stages.append(stage(f'{ident}:{k}:release', released-ack, [*ports, *compute],
                                inputs=dict.fromkeys(active, source)))
        triplet = scopes[(scope-1)*3:scope*3]
        require([(s['p'], s['phase']) for s in triplet] ==
                [(p, 'down' if phase else 'gate_up') for p in range(3)], 'scope triplet differs')
        if phase:
            outputs = {}
            for s in triplet:
                p = s['p']
                name = f'Down:{scope}:{p}'
                count = s['committed_words_per_way']
                values[name] = count*16
                outputs[window(name, sites[p], s['output_s_word_by_way'][0], count)] = name
                live_out.append(name)
        else:
            limit = (triplet[0]['stripe_first']+triplet[0]['stripe_width'])//128
            outputs = {f'Mid:{k}': f'Mid:{k}' for k in range(written_mid, limit)}
            written_mid = limit
        gap = (total-(end_trace-start_trace) if scope == last
               else grouped[scope+1][0]['start']-trace[-1]['released'])
        stages.append(stage(ident+':scope-terminal', gap, ['outer', *ports], outputs=outputs))
        task = {'id': ident, 'after': [tasks[-1]['id']] if tasks else [],
                'bindings': [{'id': ident, 'site': 'P0', 'ticks': sum(services[s['service']]['ticks'] for s in stages),
                              'resources': [], 'scratch_words': 0, 'nets': [], 'event_stages': stages}]}
        tasks.append(task)
    require(written_mid == 86 and sum(values[v] for v in live_out) == 512*16,
            'unexpected Mid or Down output coverage')
    hardware = {'resources': resources, 'sites': {p: {'bytes': 16384, 'words': 1024} for p in sites}, 'nets': {},
                'event_model': {'kind': 'qualified-event-model-v1', 'windows': windows, 'value_bytes': values,
                                'services': services, 'routes': {}, 'initial_copies': initial_copies,
                                'live_out': live_out}}
    return tasks, hardware, {'ddr_read_bytes': ddr_reads, 'local_write_receipt_bytes': local_writes,
                              'rtl_gate_cycles': gate['cycles'], 'rtl_down_cycles': down['cycles'],
                              'rtl_gate_copy_words': gate['S_copy'], 'rtl_down_copy_words': down['S_copy_words'],
                              'down_result_words': down['result_words'],
                              'mid_tiles_by_owner': [sum(windows[f'Mid:{k}']['site'] == p for k in range(86))
                                                     for p in sites[:3]]}


def run(archive, job, seed, mode, initial):
    rows, summary, oracle = load_case(archive, job, seed, mode, initial)
    tasks, hardware, observed = make_problem(rows, summary, oracle)
    outcome = {'job': job, 'seed': seed, 'mode': mode, 'initial': initial, 'observed': observed, 'plans': {}}
    expected_copy = []
    phase_start = {}
    for row in rows:
        phase = row['phase']
        phase_start.setdefault(phase, row['start'])
        offset = phase*observed['rtl_gate_cycles'] - phase_start[phase]
        expected_copy.append((offset+row['header'], offset+row['copy']))
    greedy = None
    for name, width in (('greedy', 1), ('dp', 8)):
        start = perf_counter()
        plan = search(tasks, hardware, width=width, ready_limit=4, backbone=greedy)
        seconds = perf_counter()-start
        require(plan['status'] == 'planned', 'fixed Qwen replay was not schedulable')
        verify(tasks, hardware, (), plan)
        require(plan['tasks'][57]['end'] == observed['rtl_gate_cycles']
                and plan['makespan'] == observed['rtl_gate_cycles']+observed['rtl_down_cycles'],
                'event replay disagrees with frozen phase timing')
        counts = Counter()
        actual_copy = []
        for row in plan['tasks']:
            for event in row['evaluation']['events']:
                if event['kind'] == 'stage' and event['service'].endswith(':copy'):
                    actual_copy.append((event['start'], event['end']))
                    counts['down' if row['id'] >= 'scope-59' else 'gate'] += 16*len(event['outputs'])
        require(actual_copy == expected_copy, 'individual COPY issue or ACK differs from receipt')
        require((counts['gate'], counts['down']) ==
                (observed['rtl_gate_copy_words'], observed['rtl_down_copy_words']),
                'replayed COPY words differ')
        require((plan['external_read_bytes'], plan['external_write_bytes']) == (0, 0),
                'activation replay used DDR')
        if greedy is None:
            greedy = plan
        outcome['plans'][name] = {'width': width, 'ticks': plan['makespan'], 'expanded': plan['expanded'],
                                  'elapsed_seconds': round(seconds, 6),
                                  'activation_ddr_bytes': 0, 'gate_copy_words': counts['gate'],
                                  'down_copy_words': counts['down']}
    return outcome


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    parser.add_argument('--job', type=int, default=102603)
    parser.add_argument('--seed', type=int, default=25001)
    parser.add_argument('--mode', type=int, default=0)
    parser.add_argument('--initial', type=int, default=0)
    args = parser.parse_args()
    print(json.dumps(run(args.archive, args.job, args.seed, args.mode, args.initial), indent=2))


if __name__ == '__main__':
    main()
