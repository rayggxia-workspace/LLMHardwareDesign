import unittest

from benchmark_auto_tile import mixed_problem
from event_lowering import signature
from event_tiling import discover_tiles
from run import compile_event_graph, compile_event_ir


class AutomaticTileSearchTest(unittest.TestCase):
    def test_scans_graph_with_untiled_tail_for_three_operator_pairs(self):
        for case in ('matmul-softmax', 'matmul-relu', 'add-rmsnorm'):
            with self.subTest(case=case):
                model, hardware = mixed_problem(4, case)
                self.assertNotIn('tile_groups', hardware['event_model'])
                whole = compile_event_graph(model, hardware, tile_depth=0)
                tiled = compile_event_graph(model, hardware, emit_dependencies=True)
                self.assertEqual(tiled['selected_tile_groups'][0]['nodes'], ['consume', 'produce'])
                self.assertLess(tiled['plan']['makespan'], whole['plan']['makespan'])
                self.assertIn('finish', [row['id'] for row in tiled['plan']['tasks']])
                self.assertTrue(tiled['verification']['passed'])
                self.assertFalse(tiled['phase_dependencies']['completion_only_blockers'])

    def test_depth_prunes_partial_operator_chain(self):
        model, hardware = mixed_problem(4, chain=True)
        narrow = compile_event_graph(model, hardware, tile_depth=1)
        wide = compile_event_graph(model, hardware, tile_depth=3)
        self.assertEqual(len(narrow['selected_tile_groups'][0]['nodes']), 3)
        self.assertGreater(narrow['plan']['tile_depth_pruned'], 0)
        self.assertEqual(wide['plan']['tile_depth_pruned'], 0)
        self.assertLess(narrow['plan']['expanded'], wide['plan']['expanded'])
        self.assertEqual(narrow['plan']['makespan'], wide['plan']['makespan'])

    def test_recompile_preserves_depth_from_emitted_ir(self):
        model, hardware = mixed_problem(4, chain=True)
        result = compile_event_graph(model, hardware, tile_depth=1)
        self.assertEqual(result['event_ir']['tile_depth_limit'], 1)
        retry = compile_event_ir(result['event_ir'], result['resolved_hardware'], emit_outputs=True)
        self.assertEqual(retry['plan']['tile_depth_limit'], 1)
        self.assertEqual(retry['plan']['makespan'], result['plan']['makespan'])
        self.assertGreater(retry['plan']['tile_depth_pruned'], 0)

    def test_finds_both_tile_widths_from_recipes_and_checks_boundary_join(self):
        model, hardware = mixed_problem(4, chain=True)
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

    def test_prefers_whole_plan_if_tiling_is_slower(self):
        model, hardware = mixed_problem(4)
        hardware['event_model']['services']['join']['ticks'] = 100
        result = compile_event_graph(model, hardware)
        self.assertEqual(result['status'], 'planned')
        self.assertEqual(result['selected_tile_groups'], [])
        self.assertEqual(len(result['tile_search']['layouts']), 2)
