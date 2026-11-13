"""Price complete three-P FFN candidates through the regular event compiler."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
from time import perf_counter

from ffn_program_cost import INPUT_BYTES, READ_BYTES, RESOURCES, RESULT_BYTES
from run import compile_event_ir
from verify_cover_frontier import verify


def problem(start, mode, seed, variants):
    operands = {'input': 'activation'}
    outputs = {f'result-{p}': f'result-{p}' for p in range(len(RESULT_BYTES))}
    windows = {'input': {'site': 'U', 'offset': 0, 'bytes': INPUT_BYTES}}
    windows.update({name: {'site': f'P{p}', 'offset': 0, 'bytes': RESULT_BYTES[p]}
                    for p, name in enumerate(outputs)})
    services = {'launch': {'ticks': start, 'claims': {}}, 'consumer': {'ticks': 1, 'claims': {}}}
    hardware = {
        'sites': {site: {'words': 1024, 'bytes': 16384} for site in ('U', 'P0', 'P1', 'P2')},
        'resources': RESOURCES.copy(), 'nets': {},
        'event_model': {
            'kind': 'qualified-event-model-v1', 'timing': 'replay', 'windows': windows,
            'value_bytes': {'activation': INPUT_BYTES, **{name: window['bytes'] for name, window in windows.items()
                                                         if name in outputs}},
            'routes': {}, 'initial_copies': operands, 'services': services,
        },
    }

    def binding(name, ticks=1, *, inputs=None, output=None):
        return {'id': name, 'site': 'P0', 'ticks': ticks, 'resources': [], 'nets': [], 'scratch_words': 0,
                'event_stages': [{'service': name, 'inputs': inputs or {}, 'outputs': output or {}}]}

    candidates = []
    for name, delay, lookahead in variants:
        services[name] = {'ticks': 1, 'claims': RESOURCES.copy(), 'read_bytes': READ_BYTES,
                          'ffn_program': {'mode': mode, 'seed': seed, 'lookahead': lookahead,
                                          'copy_delay_epoch': delay}}
        candidates.append(binding(name, inputs=operands, output=outputs))
    tasks = [{'id': 'launch', 'bindings': [binding('launch', start)]},
             {'id': 'ffn', 'after': ['launch'], 'bindings': candidates},
             {'id': 'consumer', 'after': ['ffn'], 'bindings': [binding('consumer', inputs=outputs)]}]
    return {'tasks': tasks}, hardware


def compare(evidence, mode, seed, variants, *, tamper=False):
    expected = {name: json.loads((evidence / f'105339-{name}.json').read_text(encoding='utf-8'))
                for name, _, _ in variants}
    start, = {row['start'] for row in expected.values()}
    model, hardware = problem(start, mode, seed, variants)
    found = {}
    for binding in model['tasks'][1]['bindings']:
        name = binding['id']
        forced = deepcopy(model)
        forced['tasks'][1]['bindings'] = [binding]
        before = perf_counter()
        result = compile_event_ir(forced, hardware, width=1)
        plan = result['plan']
        row = plan['tasks'][1]
        receipt = row['evaluation']['events'][0]['ffn_program']
        oracle = expected[name]
        if (receipt != {'result_tick': oracle['result_accept'], 'read_bytes': oracle['read_bytes'],
                        'write_bytes': oracle['write_bytes']}
                or plan['external_read_bytes'] != oracle['read_bytes'] or plan['external_write_bytes'] != 0
                or plan['tasks'][2]['start'] != receipt['result_tick'] + 1):
            raise ValueError(f'{name} full-program result, traffic or visibility differs')
        found[name] = {**receipt, 'seconds': round(perf_counter() - before, 3)}
    winners = {name for name, data in found.items()
               if data['result_tick'] == min(row['result_tick'] for row in found.values())}
    selected = {}
    for width in (1, 8):
        plan = compile_event_ir(model, hardware, width=width)['plan']
        selected[width] = plan['tasks'][1]['binding']
        if selected[width] not in winners:
            raise ValueError('full FFN candidate selection differs from the archive')
    if tamper:
        for field in ('result_tick', 'read_bytes', 'write_bytes'):
            bad = deepcopy(plan)
            bad['tasks'][1]['evaluation']['events'][0]['ffn_program'][field] -= 1
            try:
                verify(model['tasks'], hardware, (), bad)
            except ValueError as error:
                if 'FFN program retirement or traffic differs' not in str(error):
                    raise
            else:
                raise ValueError(f'FFN audit accepted a changed {field}')
    return {'candidates': found, 'winners': sorted(winners), 'selected': selected}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('evidence', type=Path)
    parser.add_argument('case', choices=('pressured-copy', 'early-copy', 'lookahead'))
    args = parser.parse_args()
    cases = {
        'pressured-copy': (1, 25001, (('baseline', 0, True), ('candidate', 21, True))),
        'early-copy': (0, 25002, (('mode0', 0, True), ('early', 1, True))),
        'lookahead': (1, 25001, (('baseline', 0, True), ('noahead', 0, False))),
    }
    print(json.dumps(compare(args.evidence, *cases[args.case], tamper=args.case == 'early-copy')))
