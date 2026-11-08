from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from search import route
from check import verify


def sample():
    via = {'cut': 2, 'lower_enclosure': 0, 'upper_enclosure': 0, 'spacing': 1}
    return {'schema_version': 'upper-router/1', 'units': 'dbu',
            'technology': {'bounds': [0, 0, 80, 80], 'origin': [8, 8], 'pitch': 8,
                           'width': 2, 'spacing': 1, 'via10': deepcopy(via), 'via11': deepcopy(via)},
            'pins': {'source': [[6, 6, 10, 10]], 'sink': [[70, 70, 74, 74]]},
            'nets': [{'id': 'bus.bit.any_name', 'driver': 'source', 'sinks': ['sink']}],
            'context': {'test_only': True}}


class RouterTests(unittest.TestCase):
    def test_shortest_unobstructed(self):
        spec = sample()
        r = route(spec)
        self.assertEqual(r['status'], 'geometry_complete')
        self.assertEqual(r['geometry_check']['wire_length_dbu'], 128)
        self.assertEqual(r['geometry_check']['via10_count'], 2)
        self.assertEqual(r['geometry_check']['via11_count'], 2)
        self.assertFalse(r['physical_qualified'])

    def test_obstacle_detour(self):
        spec = sample()
        spec['pins']['sink'] = [[70, 6, 74, 10]]
        spec['obstacles'] = [{'layer': 'M11', 'rect': [30, 4, 34, 12]}]
        r = route(spec)
        self.assertEqual(r['status'], 'geometry_complete')
        self.assertGreater(r['geometry_check']['wire_length_dbu'], 64)

    def test_access_is_selected_with_route(self):
        spec = sample()
        spec['pins']['source'] = [[6, 6, 26, 10]]
        spec['obstacles'] = [{'layer': 'M11', 'rect': [6, 6, 10, 10]}]
        r = route(spec)
        v = next(v for v in r['routes']['bus.bit.any_name']['via10'] if v['pin'] == 'source')
        self.assertNotEqual(v['at'], [8, 8])
        self.assertIn(v['at'][0], [16, 24])

    def test_multisink_tree(self):
        spec = sample()
        spec['pins']['second'] = [[70, 6, 74, 10]]
        spec['nets'][0]['sinks'].append('second')
        r = route(spec)
        self.assertEqual(r['status'], 'geometry_complete')
        self.assertEqual(r['geometry_check']['via10_count'], 3)
        self.assertLessEqual(r['geometry_check']['wire_length_dbu'], 128)

    def test_ripup_rescues_blocked_terminal(self):
        spec = sample()
        spec['pins'] = {'a0': [[6, 6, 10, 10]], 'a1': [[70, 6, 74, 10]],
                        'b0': [[38, 6, 42, 10]], 'b1': [[38, 70, 42, 74]]}
        spec['nets'] = [{'id': 'a', 'driver': 'a0', 'sinks': ['a1']},
                        {'id': 'b', 'driver': 'b0', 'sinks': ['b1']}]
        once = route(spec, rounds=1)
        retried = route(spec, rounds=4)
        self.assertEqual(once['status'], 'partial')
        self.assertEqual(retried['status'], 'geometry_complete')
        self.assertGreater(len(retried['attempts']), 1)

    def test_enclosure_not_pin_center(self):
        spec = sample()
        spec['technology']['via10']['lower_enclosure'] = 2
        r = route(spec, rounds=1)
        self.assertEqual(r['failed']['bus.bit.any_name'], 'grid_access_not_found')

    def test_cut_obstacle_blocks_switching(self):
        spec = sample()
        spec['obstacles'] = [{'layer': 'V11', 'rect': [0, 0, 80, 80]}]
        r = route(spec, rounds=1)
        self.assertEqual(r['status'], 'partial')
        self.assertEqual(r['failed']['bus.bit.any_name'], 'search_not_found')

    def test_budget_failure_is_not_infeasible(self):
        r = route(sample(), rounds=1, max_expansions=1)
        self.assertEqual(r['failed']['bus.bit.any_name'], 'search_budget_exhausted')

    def test_native_only_net(self):
        spec = sample()
        spec['nets'][0]['sinks'] = []
        r = route(spec)
        self.assertEqual(r['status'], 'geometry_complete')
        self.assertEqual(r['geometry_check']['via10_count'], 0)

    def test_invalid_grid_and_negative_cost(self):
        spec = sample()
        spec['technology']['pitch'] = 2
        with self.assertRaisesRegex(ValueError, 'pitch'):
            route(spec)
        spec = sample()
        spec['technology']['via_cost'] = -1
        with self.assertRaisesRegex(ValueError, 'negative'):
            route(spec)

    def test_duplicate_pin_across_nets(self):
        spec = sample()
        spec['nets'].append({'id': 'other', 'driver': 'source', 'sinks': []})
        with self.assertRaisesRegex(ValueError, 'different nets'):
            route(spec)

    def test_checker_rejects_removed_via(self):
        spec = sample()
        r = route(spec)
        r['routes']['bus.bit.any_name']['via11'].pop()
        with self.assertRaisesRegex(ValueError, 'disconnected'):
            verify(spec, r)

    def test_checker_rejects_missing_ack_or_bit_pin(self):
        spec = sample()
        r = route(spec)
        r['routes']['bus.bit.any_name']['via10'].pop()
        with self.assertRaisesRegex(ValueError, 'terminal access'):
            verify(spec, r)

    def test_checker_rejects_wrong_layer_and_false_coverage(self):
        spec = sample()
        r = route(spec)
        r['routes']['bus.bit.any_name']['segments'][0]['layer'] = 'M9'
        with self.assertRaisesRegex(ValueError, 'layer'):
            verify(spec, r)
        r = route(spec)
        r['routes'] = {}
        with self.assertRaisesRegex(ValueError, 'coverage'):
            verify(spec, r)

    def test_checker_rejects_changed_technology(self):
        spec = sample()
        r = route(spec)
        spec['technology']['spacing'] = 2
        with self.assertRaisesRegex(ValueError, 'fingerprint'):
            verify(spec, r)

    def test_checker_rejects_fabricated_sta_pass(self):
        spec = sample()
        r = route(spec)
        r['timing_status'] = 'passed'
        with self.assertRaisesRegex(ValueError, 'claim'):
            verify(spec, r)

    def test_deterministic_and_arbitrary_names(self):
        spec = sample()
        spec['nets'][0]['id'] = 'customer/dense/interface[37]'
        self.assertEqual(route(spec, seed=12), route(spec, seed=12))

    def test_cli(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'input.json').write_text(json.dumps(sample()))
            cmd = [sys.executable, '-B', str(Path(__file__).with_name('run.py')), str(root/'input.json'), str(root/'route.json')]
            first = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(first.returncode, 0, first.stderr)
            check = subprocess.run(cmd[: -1]+[str(root/'check.json'), '--check', str(root/'route.json')], capture_output=True, text=True)
            self.assertEqual(check.returncode, 0, check.stderr)
            self.assertTrue(json.loads((root/'check.json').read_text())['passed'])

    def test_request_adapter_and_feedback(self):
        from adapter import bind_request, failure_feedback
        from route_contract import VERSION, digest, elaborate
        spec = sample()
        base = {'schema_version': VERSION, 'base_id': 'synthetic', 'state': 'candidate', 'dbu_per_micron': 2000,
                'views': {k: {'path': 'synthetic', 'sha256': '0'*64} for k in ('odb', 'netlist', 'gds')},
                'endpoints': {pin: {'odb_term': pin, 'native_net': pin, 'role': 'driver' if pin == 'source' else 'sink',
                                    'm10_shapes': [{'layer': 'M10', 'object': 'synthetic', 'rect_dbu': rect} for rect in rects]}
                              for pin, rects in spec['pins'].items()}}
        catalog = {'schema_version': VERSION, 'demands': {'bundle': {'signals': [
            {'name': 'bit', 'width': 1, 'driver': 'source', 'sinks': ['sink']}]}}}
        request = elaborate({'bundle': []}, catalog, base, {})
        adapted = bind_request(request, base, spec['technology'])
        r = route(adapted, max_expansions=1)
        f = failure_feedback(request, r, 'synthetic-test')
        self.assertEqual(f['observations'][0]['code'], 'search_budget_exhausted')
        self.assertFalse(f['observations'][0]['hard_constraint'])
        base['base_id'] = 'moved'
        with self.assertRaisesRegex(ValueError, 'stale'):
            bind_request(request, base, spec['technology'])

    def test_128_bit_geometry_without_model_rules(self):
        spec = sample()
        spec['technology']['bounds'] = [0, 0, 80, 1040]
        spec['pins'] = {}
        spec['nets'] = []
        for i in range(128):
            y = 8+i*8
            a, b = 'tx/'+str(i), 'rx/'+str(i)
            spec['pins'][a] = [[6, y-2, 10, y+2]]
            spec['pins'][b] = [[70, y-2, 74, y+2]]
            spec['nets'].append({'id': 'arbitrary-data['+str(i)+']', 'driver': a, 'sinks': [b]})
        result = route(spec, rounds=1)
        self.assertEqual(result['status'], 'geometry_complete')
        self.assertEqual(result['geometry_check']['via10_count'], 256)

    def test_single_net_cost_against_independent_grid_dijkstra(self):
        # Independent point-graph oracle for this subset: each 2x2 obstacle
        # blocks exactly one grid vertex on one layer. No shared router rules.
        import heapq
        import random
        rng = random.Random(228)
        for _ in range(30):
            spec = sample()
            spec['technology']['bounds'] = [0, 0, 48, 48]
            spec['technology']['via_cost'] = 3
            spec['pins']['sink'] = [[38, 38, 42, 42]]
            blocked = set()
            for _ in range(rng.randrange(10)):
                state = (rng.randrange(1, 6)*8, rng.randrange(1, 6)*8, rng.choice([11, 12]))
                if state not in ((8, 8, 11), (40, 40, 11)):
                    blocked.add(state)
            spec['obstacles'] = [{'layer': 'M'+str(l), 'rect': [x-1, y-1, x+1, y+1]} for x, y, l in sorted(blocked)]
            queue = [(0, (8, 8, 11))]
            seen = {}
            answer = None
            while queue:
                cost, state = heapq.heappop(queue)
                if state in seen:
                    continue
                seen[state] = cost
                if state == (40, 40, 11):
                    answer = cost
                    break
                x, y, layer = state
                targets = [(x+8, y, layer), (x-8, y, layer)] if layer == 11 else [(x, y+8, layer), (x, y-8, layer)]
                targets.append((x, y, 23-layer))
                for target in targets:
                    if 8 <= target[0] <= 40 and 8 <= target[1] <= 40 and target not in blocked:
                        heapq.heappush(queue, (cost+(3 if target[2] != layer else 8), target))
            result = route(spec, rounds=1)
            if answer is None:
                self.assertEqual(result['status'], 'partial')
            else:
                self.assertEqual(result['status'], 'geometry_complete')
                check = result['geometry_check']
                self.assertEqual(check['wire_length_dbu']+3*check['via11_count'], answer)


if __name__ == '__main__':
    unittest.main()
