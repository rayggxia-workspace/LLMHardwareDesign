"""Replay the S32 range-scan, factor and in-place apply storage contract."""
import argparse
from hashlib import sha256
import json
from pathlib import Path

from benchmark_attention_kv import typed_route
from run import compile_event_ir


ROW_BYTES = 2048 * 4
PORT = 'U.S.port'
CONTEXT = 'U.rms.context'


def archived_gamma(program_directory, manifest, layer):
    raw = (program_directory / 'program.json').read_bytes()
    receipt = json.loads((program_directory / 'receipt.json').read_bytes())
    if sha256(raw).hexdigest() != receipt['program_sha256'] or not receipt['passed']:
        raise ValueError('integer program differs from its receipt')
    program = json.loads(raw)
    parameter = f'model.layers.{layer}.input_layernorm.weight'
    kernel = f'/model/model/layers.{layer}/input_layernorm/Mul_1'
    nodes = [node for node in program['instructions'] if node['kernel'] == kernel]
    (factor,) = [node for node in nodes if node['op'] == 'NFactorAdaptive']
    (square_sum,) = [node for node in nodes if node['op'] == 'SquareSum']
    output = nodes[-1]
    if (factor['bits'] != 32 or square_sum['attributes']['length'] != 2048
            or output['op'] != 'Product' or output['shape'] != [1, 1, 2048] or output['bits'] != 32
            or output['inputs'][-1] != f'model.{parameter}'):
        raise ValueError('archived S32 input normalization geometry differs')
    (gamma,) = [record for record in json.loads(manifest.read_bytes())['records']
                if record['parameter'] == parameter and record['role'] == 'rms_gamma']
    data = (manifest.parent / gamma['image']).read_bytes()
    if (gamma['encoding'] != 's32-le-rne' or gamma['address'] % 128 or len(data) != ROW_BYTES
            or gamma['bytes'] != ROW_BYTES or sha256(data).hexdigest() != gamma['sha256']):
        raise ValueError('S32 gamma image differs')
    return gamma['address'], {'program_sha256': receipt['program_sha256'], 'gamma_sha256': gamma['sha256'],
                              'factor': factor['id'], 'output': output['id']}


def problem(address, *, gamma_at_entry, ticks_per_word, queue, preserve_old=False):
    # The archived component uses 512 S128 words in each half of one SRAM.
    # Phase lengths are configurable model inputs, expressed per S128 word.
    phases = [{'kind': name, 'ticks': 512 * ticks, 'claims': {PORT: 1}}
              for name, ticks in zip(('scan', 'stats', 'apply'), ticks_per_word)]
    timing = {'input_reads': {'row': ['scan', 'apply'],
                              'gamma': ['scan' if gamma_at_entry else 'apply', 'apply']},
              'in_place': ['row'], 'write': 'apply', 'publish': 'apply', 'result_hold': CONTEXT}
    rms = {'ticks': sum(p['ticks'] for p in phases), 'claims': {}, 'phases': phases,
           'hold_claims': {CONTEXT: 1}, 'window_phases': timing}

    def task(name, service, inputs, outputs, ticks=1, after=()):
        return {'id': name, 'after': list(after), 'bindings': [{
            'id': name, 'site': 'U', 'ticks': ticks, 'resources': [], 'nets': [], 'scratch_words': 0,
            'event_stages': [{'service': service, 'inputs': inputs, 'outputs': outputs}]}]}

    tasks = [task('rms', 'rms', {'row': 'before', 'gamma': 'gamma'}, {'row': 'after'}, rms['ticks']),
             task('use-output', 'use', {'row': 'after'}, {}, after=('rms',))]
    if preserve_old:
        tasks.append(task('restore-input', 'use', {'row': 'before'}, {}, after=('use-output',)))
    live = ['after'] if not preserve_old else []
    backing = {'gamma': address, 'before': 0x300000000}
    return {'tasks': tasks}, {
        'sites': {'U': {'words': 1024, 'bytes': 2 * ROW_BYTES}},
        'resources': {PORT: 1, CONTEXT: 1}, 'nets': {},
        'event_model': {
            'kind': 'qualified-event-model-v1', 'timing': 'replay',
            'windows': {name: {'site': 'U', 'offset': i * ROW_BYTES, 'bytes': ROW_BYTES}
                        for i, name in enumerate(('row', 'gamma'))},
            'value_bytes': dict.fromkeys(('before', 'gamma', 'after'), ROW_BYTES),
            'services': {'rms': rms, 'use': {'ticks': 1, 'claims': {PORT: 1}}},
            'initial_copies': {'row': 'before'}, 'initial_backing': ['gamma'], 'live_out': live,
            'routes': {'load': typed_route('DDR', 'U', 4, PORT), 'store': typed_route('U', 'DDR', 3, PORT)},
            'typed_dma': {'addresses': backing, 'return_latency': [7, 8],
                          'mixed': {'queue': queue, 'write_latency': 9}},
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('program_directory', type=Path)
    parser.add_argument('manifest', type=Path)
    parser.add_argument('--layer', type=int, default=1)
    parser.add_argument('--queue', type=int, default=16)
    parser.add_argument('--ticks-per-word', type=int, nargs=3, required=True, metavar=('SCAN', 'STATS', 'APPLY'))
    parser.add_argument('--preserve-old', action='store_true')
    args = parser.parse_args()
    address, evidence = archived_gamma(args.program_directory, args.manifest, args.layer)
    for early in (True, False):
        model, hardware = problem(address, gamma_at_entry=early, ticks_per_word=args.ticks_per_word,
                                  queue=args.queue, preserve_old=args.preserve_old)
        plan = compile_event_ir(model, hardware, width=1)['plan']
        expected = (ROW_BYTES * (1 + args.preserve_old), ROW_BYTES * args.preserve_old)
        if plan['status'] != 'planned' or (plan['external_read_bytes'], plan['external_write_bytes']) != expected:
            raise ValueError(f'S32 RMS or old-version traffic differs: {plan}')
        rms, consumer, *_ = plan['tasks']
        events = rms['evaluation']['events']
        update = events[-1]
        gamma, = [event for event in events if event.get('value') == 'gamma']
        if consumer['start'] < update['end'] or gamma['end'] > update['phases'][2]['start']:
            raise ValueError('S32 RMS input or output custody differs')
        print(json.dumps({**evidence, 'gamma_address': address, 'gamma_at_entry': early,
                          'phases': update['phases'], 'gamma_ack': gamma['end'], 'makespan': plan['makespan'],
                          'traffic': expected}, sort_keys=True))


if __name__ == '__main__':
    main()
