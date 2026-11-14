"""Compare row interleaving with an all-rows barrier on the same task costs."""
import argparse
from copy import deepcopy
import json
from time import perf_counter

from benchmark_tile_handoff import binding, hardware, stage, window
from event_lowering import lower, value_size
from run import compile_event_ir


def problem(rows, slots, columns=513, case='matmul-softmax'):
    producer, consumer, attrs = {
        'matmul-softmax': ('MatMul', 'Softmax', {'axis': -1}),
        'matmul-relu': ('MatMul', 'Relu', {}),
        'add-rmsnorm': ('Add', 'RMSNormalization', {'axis': -1}),
    }[case]
    row = {'shape': [1, columns], 'dtype': 'INT32'}
    scores = {**row, 'shape': [rows, columns]}
    query = {'shape': [rows, 128], 'dtype': 'INT32'} if producer == 'MatMul' else scores
    key = {'shape': [128, columns], 'dtype': 'INT32'} if producer == 'MatMul' else scores
    graph = {'inputs': ['q', 'kt'], 'outputs': ['y'],
             'values': {'q': query, 'kt': key, 'x': scores, 'y': scores},
             'tasks': [
                 {'id': 'produce', 'op': producer, 'inputs': ['q', 'kt'], 'outputs': ['x']},
                 {'id': 'consume', 'op': consumer, 'attributes': dict(attrs),
                  'inputs': ['x'], 'outputs': ['y']},
             ]}
    windows = {}

    def reserve(name, size):
        offset = sum(region['bytes'] for region in windows.values())
        windows[name] = window('P0', offset, ((size + 15) // 16) * 16)

    reserve('q', value_size(query))
    reserve('kt', value_size(key))
    for i in range(slots):
        reserve(f'x{i}', columns * 4)
    for i in range(rows):
        reserve(f'y{i}', columns * 4)
    reserve('result', rows * columns * 4)
    produce_ticks, consume_ticks = {'matmul-softmax': (8, 5), 'matmul-relu': (8, 2),
                                    'add-rmsnorm': (3, 7)}[case]
    services = {
        'produce': {'ticks': produce_ticks, 'claims': {'Producer': 1}},
        'consume': {'ticks': consume_ticks, 'claims': {'Consumer': 1}},
        'join': {'ticks': rows, 'claims': {'S': 1}},
    }
    arch = hardware({'P0': sum(w['bytes'] for w in windows.values())},
                    ('Producer', 'Consumer', 'S'), windows, {}, services)
    arch['event_model']['initial_copies'] = {'q': 'q', 'kt': 'kt'}
    arch['event_model']['tile_groups'] = [
        {'nodes': ['produce', 'consume'], 'axes': {'x': 0, 'y': 0}, 'tile_size': 1}]
    recipes = []
    for i in range(rows):
        recipes.append({'op': producer, 'inputs': [query, key], 'outputs': [row],
                        'tile': {'start': i, 'stop': i + 1, 'input_axes': [None, None], 'output_axes': [0]},
                        'binding': binding(f'produce-{i}', 'P0', [
                            stage('produce', inputs={'q': 'in:0', 'kt': 'in:1'},
                                  outputs={f'x{i % slots}': 'out:0'})])})
    for i in range(rows):
        recipes.append({'op': consumer, 'inputs': [row], 'outputs': [row], 'attributes': dict(attrs),
                        'tile': {'start': i, 'stop': i + 1, 'input_axes': [0], 'output_axes': [0]},
                        'binding': binding(f'consume-{i}', 'P0', [
                            stage('consume', inputs={f'x{i % slots}': 'in:0'},
                                  outputs={f'y{i}': 'out:0'})])})
    recipes.append({'op': 'Concat', 'inputs': [row] * rows, 'outputs': [scores],
                    'attributes': {'axis': 0}, 'binding': binding('join', 'P0', [
                        stage('join', inputs={f'y{i}': f'in:{i}' for i in range(rows)},
                              outputs={'result': 'out:0'})])})
    arch['event_model']['recipes'] = recipes
    return graph, arch

def compare(rows, slots, width, columns, barrier, case='matmul-softmax'):
    graph, arch = problem(rows, slots, columns, case)
    started = perf_counter()
    ir, resolved = lower(graph, arch)
    producers = [t['id'] for t in ir['tasks'] if t['id'].startswith('produce::tile::')]
    if barrier:
        ir = deepcopy(ir)
        for task in ir['tasks']:
            if task['id'].startswith('consume::tile::'):
                task['after'] = sorted(set(task['after']) | {producers[-1]})
    result = compile_event_ir(ir, resolved, width=width, emit_outputs=True, emit_dependencies=True)
    elapsed = perf_counter() - started
    plan = result['plan']
    report = {'case': case, 'rows': rows, 'columns': columns, 'slots': slots, 'width': width,
              'policy': 'barrier' if barrier else 'tile-dp', 'status': result['status'],
              'seconds': round(elapsed, 4),
              'expanded': plan['expanded'], 'peak_bucket_states': plan['peak_bucket_states']}
    if plan['status'] != 'planned':
        return report
    assert result['verification']['passed']
    assert not result['phase_dependencies']['completion_only_blockers']
    intervals, consumers = {}, {}
    for row in plan['tasks']:
        for event in row['evaluation']['events']:
            if event.get('service') == 'produce':
                value, = event['outputs'].values()
                intervals[value] = [event['start'], event['end']]
            elif event.get('service') == 'consume':
                value, = event['inputs'].values()
                consumers[value] = event['end']
    assert len(intervals) == len(consumers) == rows
    for value, interval in intervals.items():
        assert interval[1] <= consumers[value]
        interval[1] = consumers[value]
    timeline = sorted({tick for interval in intervals.values() for tick in interval})
    peak = max(sum(lo <= tick < hi for lo, hi in intervals.values()) for tick in timeline)
    report.update(ticks=plan['makespan'], intermediate_peak_bytes=peak * columns * 4,
                  intermediate_peak_tiles=peak, pruned=plan['pruned'],
                  ddr_bytes=plan['external_read_bytes'] + plan['external_write_bytes'],
                  dispatches=len(result['outputs']['program']['mother']) - 1)
    if rows <= 4:
        report['order'] = [row['id'] for row in plan['tasks']]
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case', choices=('matmul-softmax', 'matmul-relu', 'add-rmsnorm'),
                        default='matmul-softmax')
    parser.add_argument('--rows', type=int, required=True)
    parser.add_argument('--slots', type=int)
    parser.add_argument('--width', type=int, default=8)
    parser.add_argument('--columns', type=int, default=513)
    parser.add_argument('--barrier', action='store_true')
    args = parser.parse_args()
    slots = args.rows if args.slots is None else args.slots
    if args.rows < 2 or not 1 <= slots <= args.rows or args.columns < 1:
        parser.error('require at least two rows, positive columns and one to rows score slots')
    print(json.dumps(compare(args.rows, slots, args.width, args.columns, args.barrier, args.case)))


if __name__ == '__main__':
    main()
