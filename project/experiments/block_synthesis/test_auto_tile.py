import unittest

from benchmark_tile_handoff import binding, hardware, stage, window
from event_lowering import signature, value_size
from event_tiling import discover_tiles, lower_tiles
from run import compile_event_graph, compile_event_ir


def _tile_fixture(rows, slots, columns=513, case='matmul-softmax'):
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


def _mixed_problem(rows, case='matmul-softmax', *, chain=False):
    graph, hardware = _tile_fixture(rows, rows, case=case)
    spec = hardware['event_model']
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


class AutomaticTileSearchTest(unittest.TestCase):
    def test_scans_graph_with_untiled_tail_for_three_operator_pairs(self):
        for case in ('matmul-softmax', 'matmul-relu', 'add-rmsnorm'):
            with self.subTest(case=case):
                model, hardware = _mixed_problem(4, case)
                whole = compile_event_graph(model, hardware, tile_depth=0)
                tiled = compile_event_graph(model, hardware, emit_dependencies=True)
                self.assertEqual(tiled['selected_tile_layout'][0]['nodes'], ['consume', 'produce'])
                self.assertLess(tiled['plan']['makespan'], whole['plan']['makespan'])
                self.assertIn('finish', [row['id'] for row in tiled['plan']['tasks']])
                self.assertTrue(tiled['verification']['passed'])
                self.assertFalse(tiled['phase_dependencies']['completion_only_blockers'])
                tasks = {row['id']: row for row in tiled['event_ir']['tasks']}
                self.assertEqual(tasks['consume::tile::0:1']['after'], ['produce::tile::0:1'])
                self.assertEqual(tasks['consume::tile::1:2']['after'],
                                 ['consume::tile::0:1', 'produce::tile::1:2'])
                commands = {row['task_id']: row for row in tiled['outputs']['program']['mother'][:-1]}
                self.assertEqual(commands['consume::tile::0:1']['wait_for'],
                                 [commands['produce::tile::0:1']['sequence']])

    def test_depth_prunes_partial_operator_chain(self):
        model, hardware = _mixed_problem(4, chain=True)
        narrow = compile_event_graph(model, hardware, tile_depth=1)
        wide = compile_event_graph(model, hardware, tile_depth=3)
        self.assertEqual(len(narrow['selected_tile_layout'][0]['nodes']), 3)
        self.assertGreater(narrow['plan']['tile_depth_pruned'], 0)
        self.assertEqual(wide['plan']['tile_depth_pruned'], 0)
        self.assertLess(narrow['plan']['expanded'], wide['plan']['expanded'])
        self.assertEqual(narrow['plan']['makespan'], wide['plan']['makespan'])

    def test_recompile_preserves_depth_from_emitted_ir(self):
        model, hardware = _mixed_problem(4, chain=True)
        result = compile_event_graph(model, hardware, tile_depth=1)
        self.assertEqual(result['event_ir']['tile_depth_limit'], 1)
        retry = compile_event_ir(result['event_ir'], result['resolved_hardware'], emit_outputs=True)
        self.assertEqual(retry['plan']['tile_depth_limit'], 1)
        self.assertEqual(retry['plan']['makespan'], result['plan']['makespan'])
        self.assertGreater(retry['plan']['tile_depth_pruned'], 0)

    def test_finds_both_tile_widths_from_recipes_and_checks_boundary_join(self):
        model, hardware = _mixed_problem(4, chain=True)
        recipes = hardware['event_model']['recipes']
        for recipe in list(recipes):
            tile = recipe.get('tile')
            if tile is not None and tile['start'] % 2 == 0:
                recipes.append({**recipe, 'tile': {**tile, 'stop': tile['start'] + 2},
                                'inputs': [{**desc, 'shape': [2, desc['shape'][1]]}
                                           if axis is not None else desc
                                           for desc, axis in zip(recipe['inputs'], tile['input_axes'])],
                                'outputs': [{**desc, 'shape': [2, desc['shape'][1]]}
                                            for desc in recipe['outputs']]})
        join, = (r for r in recipes if r['op'] == 'Concat')
        part = join['inputs'][0]
        recipes.append({**join, 'inputs': [{**part, 'shape': [2, part['shape'][1]]}] * 2})
        groups = discover_tiles(model, recipes, signature, 8)
        variants = [g for g in groups if len(g['nodes']) == 3]
        self.assertEqual({g['tile_size'] for g in variants}, {1, 2})
        recipes = [r for r in recipes if r['op'] != 'Concat']
        self.assertFalse(discover_tiles(model, recipes, signature, 8))

    def test_discovery_keeps_shared_consumers_and_restores_boundary_value(self):
        model, hardware = _mixed_problem(4)
        values = model['values']
        values.update(z=values['x'], w=values['x'])
        model['tasks'].extend([
            {'id': 'consume2', 'op': 'Softmax', 'attributes': {'axis': -1},
             'inputs': ['x'], 'outputs': ['z']},
            {'id': 'outside', 'op': 'Identity', 'inputs': ['x'], 'outputs': ['w']},
        ])
        model['outputs'].append('z')
        recipes = hardware['event_model']['recipes']
        join, = (r for r in recipes if r['op'] == 'Concat')
        self.assertEqual(join['outputs'], [signature(values['x'])])
        region = next(g for g in discover_tiles(model, recipes, signature, 8)
                      if len(g['nodes']) == 3)
        rewritten, _, _, _ = lower_tiles(model, [region])
        nodes = {node['id']: node for node in rewritten['tasks']}
        for name in ('consume', 'consume2'):
            self.assertEqual(nodes[f'{name}::tile::1:2']['inputs'], ['x::tile::1:2'])
        self.assertEqual(nodes['outside']['inputs'], ['x'])
        self.assertEqual(nodes['x::tile_join']['outputs'], ['x'])

    def test_declines_unqualified_reduction_axis(self):
        model, hardware = _mixed_problem(4)
        model['tasks'][1]['attributes'] = {'axis': 0}
        result = compile_event_graph(model, hardware)
        self.assertEqual(result['status'], 'blocked_lowering')
        self.assertNotIn('outputs', result)

    def test_prefers_whole_plan_if_tiling_is_slower(self):
        model, hardware = _mixed_problem(4)
        hardware['event_model']['services']['join']['ticks'] = 100
        result = compile_event_graph(model, hardware)
        self.assertEqual(result['status'], 'planned')
        self.assertEqual(result['selected_tile_layout'], [])
        self.assertEqual(len(result['tile_search']['layouts']), 2)
