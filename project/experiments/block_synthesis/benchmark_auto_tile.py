"""Evaluate automatic tile discovery and partial-operator depth on a mixed graph."""
import argparse
import json
from time import perf_counter

from benchmark_tile_handoff import binding, stage, window
from benchmark_tile_handoff_dp import problem
from event_lowering import value_size
from run import compile_event_graph


def mixed_problem(rows, case='matmul-softmax', *, chain=False):
    graph, hardware = problem(rows, rows, case=case)
    spec = hardware['event_model']
    spec.pop('tile_groups')
    model, vals = graph['tasks'], graph['values']
    score = vals['x']
    producer, consumer = model[:2]
    services, recipes = spec['services'], spec['recipes']

    def reserve(name, size):
        site = hardware['sites']['P0']
        length = ((size + 15) // 16) * 16
        spec['windows'][name] = window('P0', site['bytes'], length)
        site['bytes'] += length
        site['words'] += length // 16

    reserve('score-full', value_size(score))
    reserve('output', value_size(score))
    if chain:
        vals['z'] = score.copy()
        reserve('mid', value_size(score))
        model[1] = {**model[1], 'outputs': ['z']}
        model.insert(2, {'id': 'post', 'op': 'Relu', 'domain': 'test-chain',
                         'inputs': ['z'], 'outputs': ['y']})
        hardware['resources']['Post'] = 1
        services['post'] = {'ticks': 3, 'claims': {'Post': 1}}
        services['post-all'] = {'ticks': rows * 3, 'claims': {'Post': 1}}
        for i, recipe in enumerate([r for r in recipes if r['binding']['id'].startswith('consume-')]):
            reserve(f'z{i}', value_size(recipe['outputs'][0]))
            recipe['binding']['event_stages'][0]['outputs'] = {f'z{i}': 'out:0'}
            recipes.append({**recipe, 'op': 'Relu', 'domain': 'test-chain', 'attributes': {},
                            'binding': binding(f'post-{i}', 'P0', [
                                stage('post', inputs={f'z{i}': 'in:0'}, outputs={f'y{i}': 'out:0'})])})
        recipes.append({'op': 'Relu', 'domain': 'test-chain', 'inputs': [score],
                        'outputs': [score], 'binding': binding('post-all', 'P0', [
                            stage('post-all', inputs={'mid': 'in:0'}, outputs={'result': 'out:0'})])})
    services['produce-all'] = {'ticks': rows * services['produce']['ticks'], 'claims': {'Producer': 1}}
    services['consume-all'] = {'ticks': rows * services['consume']['ticks'] + rows,
                                'claims': {'Consumer': 1}}
    recipes.extend([
        {'op': producer['op'], 'inputs': [vals[v] for v in producer['inputs']], 'outputs': [score],
         'binding': binding('produce-all', 'P0', [
             stage('produce-all', inputs={'q': 'in:0', 'kt': 'in:1'}, outputs={'score-full': 'out:0'})])},
        {'op': consumer['op'], 'attributes': consumer['attributes'],
         'inputs': [score], 'outputs': [score],
         'binding': binding('consume-all', 'P0', [
             stage('consume-all', inputs={'score-full': 'in:0'},
                   outputs={'mid' if chain else 'result': 'out:0'})])},
        {'op': 'Identity', 'inputs': [score], 'outputs': [score],
         'binding': binding('finish', 'P0', [
             stage('join', inputs={'result': 'in:0'}, outputs={'output': 'out:0'})])},
    ])
    vals['out'] = score.copy()
    graph['outputs'] = ['out']
    model.append({'id': 'finish', 'op': 'Identity', 'inputs': ['y'], 'outputs': ['out']})
    return graph, hardware


def evaluate(rows, case, depth, width, chain):
    graph, hardware = mixed_problem(rows, case, chain=chain)
    started = perf_counter()
    result = compile_event_graph(graph, hardware, width=width, tile_depth=depth, emit_dependencies=True)
    elapsed = round(perf_counter() - started, 4)
    assert result['status'] == 'planned'
    assert result['verification']['passed']
    assert not result['phase_dependencies']['completion_only_blockers']
    return {'case': case, 'rows': rows, 'chain': chain, 'width': width, 'depth': depth,
            'seconds': elapsed, 'ticks': result['plan']['makespan'],
            'groups': result.get('selected_tile_groups', []),
            'tasks': len(result['plan']['tasks']), 'expanded': result['plan']['expanded'],
            'bucket': result['plan']['peak_bucket_states'],
            'depth_pruned': result['plan'].get('tile_depth_pruned', 0),
            'layouts': result.get('tile_search', {}).get('layouts', [])}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case', choices=('matmul-softmax', 'matmul-relu', 'add-rmsnorm'),
                        default='matmul-softmax')
    parser.add_argument('--rows', type=int, default=8)
    parser.add_argument('--depth', type=int, default=2)
    parser.add_argument('--width', type=int, default=8)
    parser.add_argument('--chain', action='store_true')
    args = parser.parse_args()
    print(json.dumps(evaluate(args.rows, args.case, args.depth, args.width, args.chain)))


if __name__ == '__main__':
    main()
