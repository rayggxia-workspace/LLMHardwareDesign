"""Algorithm invariants on explicitly synthetic unit fixtures, not benchmarks.

No fixture numbers are used to claim hardware latency, throughput, or capacity.
Native qualification and full-model evidence run separately on the server.
"""
from copy import deepcopy
import itertools
import unittest

from solver import Planner, Unsupported, optimize
from verify import verify, InvalidPlan
from seed import serial_seed


def fixture(words=8):
    hw = {'external': 'MEM', 'sites': {'left': {'words': words}, 'right': {'words': words}},
          'resources': {'left.core': 1, 'right.core': 1, 'left.port': 1, 'right.port': 1, 'mem': 1},
          'services': {}, 'routes': {}, 'nets': {}}
    for site in hw['sites']:
        hw['services'][site] = {'op': 'add', 'numeric': 'test-int16', 'site': site,
            'ticks': 3, 'resources': [site + '.core'], 'qualified': True}
    for src, dst in itertools.permutations(['MEM', 'left', 'right'], 2):
        rid = src + '>' + dst
        resources = [src + '.port'] if src != 'MEM' else ['mem']
        if dst != 'MEM':
            resources.append(dst + '.port')
        hw['routes'][rid] = {'src': src, 'dst': dst, 'qualified': True,
            'protocol': 'acknowledged_copy', 'min_words': 1, 'max_words': 8,
            'phases': [{'name': 'copy-and-ack', 'ticks': 2, 'resources': resources}], 'nets': [rid]}
        hw['nets'][rid] = {'cost': 1, 'fixed': 'MEM' in (src, dst)}
    graph = {'tasks': [{'id': 'a', 'op': 'add', 'numeric': 'test-int16', 'inputs': ['input'], 'outputs': ['a.out']},
                       {'id': 'b', 'op': 'add', 'numeric': 'test-int16', 'inputs': ['a.out'], 'outputs': ['b.out']}],
             'values': {'input': {'words': 2, 'site': 'MEM'},
                        'a.out': {'words': 2, 'producer': 'a'},
                        'b.out': {'words': 2, 'producer': 'b', 'output_site': 'MEM'}}, 'outputs': ['b.out']}
    return graph, hw


class TestPlanner(unittest.TestCase):
    def solve(self, graph, hw, **kwargs):
        plan = Planner(graph, hw, **kwargs).solve(seconds=8)
        self.assertIn('tasks', plan, plan)
        verify(graph, hw, plan, kwargs.get('wire_budget'))
        return plan

    def test_schedule_and_output_ack(self):
        g, h = fixture()
        plan = self.solve(g, h)
        self.assertEqual(plan['makespan'], 10)
        self.assertEqual(plan['status'], 'OPTIMAL')
        self.assertTrue(any(m['final'] for m in plan['moves']))

    def test_data_before_compute_and_ack_lease(self):
        g, h = fixture()
        p = self.solve(g, h, fixed={'a': 'left', 'b': 'right'})
        bad = deepcopy(p)
        bad['tasks']['b']['start'] = 0
        bad['tasks']['b']['end'] = 3
        with self.assertRaises(InvalidPlan):
            verify(g, h, bad)
        bad = deepcopy(p)
        for row in bad['allocations']:
            if row['value'] == 'a.out' and row['site'] == 'left':
                row['end'] = p['tasks']['a']['end']
        with self.assertRaises(InvalidPlan):
            verify(g, h, bad)

    def test_storage_address_collision_detected(self):
        g, h = fixture()
        p = self.solve(g, h, fixed={'a': 'left', 'b': 'left'})
        bad = deepcopy(p)
        for a in bad['allocations']:
            a['address'] = 0
        with self.assertRaises(InvalidPlan):
            verify(g, h, bad)

    def test_spill_is_real_store_then_load(self):
        g, h = fixture(words=4)
        # a's result is used after b, but b needs the complete left S as
        # scratch. c must run in left only after b. Therefore a must really
        # be stored and reloaded, even though its tile fits individually.
        g['tasks'] = [
            {'id': 'a', 'op': 'add', 'numeric': 'test-int16', 'inputs': ['input'], 'outputs': ['a.out']},
            {'id': 'b', 'op': 'scratch', 'numeric': 'test-int16', 'inputs': [], 'outputs': [], 'after': ['a']},
            {'id': 'c', 'op': 'add', 'numeric': 'test-int16', 'inputs': ['a.out'], 'outputs': ['c.out'], 'after': ['b']}]
        del g['values']['b.out']
        g['values']['c.out'] = {'words': 1, 'producer': 'c', 'output_site': 'MEM'}
        g['outputs'] = ['c.out']
        h['services']['scratch'] = {**h['services']['left'], 'op': 'scratch', 'scratch_words': 4}
        p = self.solve(g, h, fixed={'a': 'left', 'b': 'scratch', 'c': 'left'})
        self.assertTrue(any(m['value'] == 'a.out' and m['dst'] == 'MEM' for m in p['moves']))
        self.assertTrue(any(m['value'] == 'a.out' and m['src'] == 'MEM' for m in p['moves']))
        baseline = serial_seed(g, h, {'a': 'left', 'b': 'scratch', 'c': 'left'})
        self.assertTrue(any(m['value'] == 'a.out' and m['dst'] == 'MEM' for m in baseline['moves']))

    def test_stale_copy_and_cyclic_graph_rejected(self):
        g, h = fixture()
        p = self.solve(g, h, fixed={'a': 'left', 'b': 'right'})
        bad = deepcopy(p)
        for a in bad['allocations']:
            if a['value'] == 'a.out' and a['site'] == 'right':
                a['origin'] = 'initial'
        with self.assertRaises(InvalidPlan):
            verify(g, h, bad)
        g['tasks'][0]['after'] = ['b']
        with self.assertRaises(ValueError):
            Planner(g, h)

    def test_clean_external_copy_avoids_store(self):
        g, h = fixture()
        g['values']['a.out']['external_copy'] = True
        # Existing external copies are legal only for inputs; generated values
        # must not claim that an old checkpoint already contains their result.
        with self.assertRaises((Unsupported, ValueError)):
            Planner(g, h)

    def test_unsupported_numeric_never_falls_back(self):
        g, h = fixture()
        g['tasks'][0]['numeric'] = 'FLOAT'
        with self.assertRaises(Unsupported):
            Planner(g, h)

    def test_unknown_operator_attribute_never_silently_ignored(self):
        g, h = fixture()
        g['tasks'][0]['attributes'] = {'unimplemented_shift': 7}
        with self.assertRaises(Unsupported):
            Planner(g, h)

    def test_static_union_not_execution_count(self):
        g, h = fixture()
        g['tasks'].append({'id': 'c', 'op': 'add', 'numeric': 'test-int16', 'inputs': ['a.out'], 'outputs': ['c.out']})
        g['values']['c.out'] = {'words': 1, 'producer': 'c'}
        p = self.solve(g, h, fixed={'a': 'left', 'b': 'right', 'c': 'right'})
        self.assertEqual(p['wire_cost'], len([n for n in p['nets'] if not h['nets'][n]['fixed']]))
        self.assertEqual(p['nets'].count('left>right'), 1)

    def test_no_route_is_infeasible_not_magic_copy(self):
        g, h = fixture()
        h['routes'] = {}
        p = Planner(g, h).solve(seconds=3)
        self.assertEqual(p['status'], 'INFEASIBLE')

    def test_resource_replay_does_not_trust_claim_rows(self):
        g, h = fixture()
        p = self.solve(g, h, fixed={'a': 'left', 'b': 'left'})
        bad = deepcopy(p)
        bad['claims'] = []
        bad['tasks']['b'].update(start=p['tasks']['a']['start'], end=p['tasks']['a']['end'])
        with self.assertRaises(InvalidPlan):
            verify(g, h, bad)

    def test_arbitrary_resource_names_and_capacities(self):
        g, h = fixture()
        h['sites']['left']['words'] = 1024
        h['services']['left']['resources'].append('custom-local-controller')
        h['resources']['custom-local-controller'] = 1
        p = self.solve(g, h)
        self.assertLessEqual(verify(g, h, p)['peak_words'].get('left', 0), 1024)

    def test_lns_keeps_legal_incumbent(self):
        g, h = fixture()
        p = self.solve(g, h, fixed={'a': 'left', 'b': 'right'})
        q = optimize(g, h, initial=p, seconds=5, rounds=3)
        self.assertLess(q['makespan'], p['makespan'])
        self.assertTrue(q['optimization_history'])

    def test_shared_materialization_counts_one_load(self):
        g, h = fixture()
        g['tasks'][1]['inputs'] = ['input']
        p = self.solve(g, h, fixed={'a': 'left', 'b': 'left'})
        copies = [m for m in p['moves'] if m['value'] == 'input']
        self.assertEqual(len(copies), 1)

    def test_small_chain_matches_independent_closed_form_reference(self):
        # For this two-node chain, every operation depends on the preceding
        # copy/compute. Enumerating just four placements gives an independent
        # exact reference; no optimizer internals or produced claims are read.
        for left, right in [(1, 4), (5, 2), (3, 3)]:
            g, h = fixture()
            h['services']['left']['ticks'] = left
            h['services']['right']['ticks'] = right
            reference = min(2 + h['services'][a]['ticks'] + (0 if a == b else 2)
                            + h['services'][b]['ticks'] + 2 for a, b in itertools.product(['left', 'right'], repeat=2))
            p = self.solve(g, h)
            self.assertEqual(p['makespan'], reference)
            self.assertEqual(p['best_bound'], reference)

    def test_tile_signature_and_static_pin_conflict(self):
        g, h = fixture()
        for s in h['services'].values():
            s['input_words'] = [1]
        with self.assertRaises(Unsupported):
            Planner(g, h)
        g, h = fixture()
        g['tasks'].append({'id': 'c', 'op': 'add', 'numeric': 'test-int16',
                           'inputs': ['b.out'], 'outputs': ['c.out']})
        g['values']['c.out'] = {'words': 1, 'producer': 'c', 'output_site': 'MEM'}
        g['outputs'] = ['c.out']
        h['routes'] = {r: v for r, v in h['routes'].items() if r in ['MEM>left', 'left>right', 'right>left', 'left>MEM']}
        h['incompatible_routes'] = [['left>right', 'right>left']]
        p = Planner(g, h, fixed={'a': 'left', 'b': 'right', 'c': 'left'}).solve(seconds=5)
        self.assertEqual(p['status'], 'INFEASIBLE')

    def test_real_capacity_of_tile_not_entire_tensor(self):
        # A symbolic vector of any length is lowered to independent tile
        # values; no rule requires all 16 tiles to reside at the same time.
        g, h = fixture(words=3)
        g['tasks'], g['values'], g['outputs'] = [], {}, []
        for i in range(16):
            x, y = f'x{i}', f'y{i}'
            g['values'][x] = {'words': 2, 'site': 'MEM'}
            g['values'][y] = {'words': 1, 'producer': str(i), 'output_site': 'MEM'}
            g['tasks'].append({'id': str(i), 'op': 'add', 'numeric': 'test-int16', 'inputs': [x], 'outputs': [y]})
            g['outputs'].append(y)
        p = serial_seed(g, h, {str(i): 'left' for i in range(16)})
        self.assertLessEqual(verify(g, h, p)['peak_words']['left'], 3)
        self.assertEqual(p['external_words'], 48)

    def test_external_capacity_and_address_replay(self):
        g, h = fixture()
        h['external_capacity_words'] = 3
        p = Planner(g, h).solve(seconds=3)
        self.assertEqual(p['status'], 'INFEASIBLE')
        h['external_capacity_words'] = 4
        p = self.solve(g, h)
        self.assertTrue(verify(g, h, p)['external_capacity_qualified'])
        bad = deepcopy(p)
        for r in bad['external_regions']:
            r['address_words'] = 0
        with self.assertRaises(InvalidPlan):
            verify(g, h, bad)

    def test_tied_cross_layer_binding_neighborhood(self):
        g, h = fixture()
        p = Planner(g, h, tied=[['a', 'b']]).solve(seconds=4)
        verify(g, h, p)
        self.assertEqual(p['tasks']['a']['service'], p['tasks']['b']['service'])
        self.assertEqual(p['proof_scope']['tied_bindings'], [['a', 'b']])

    def test_whole_static_net_family_is_not_cut_at_layer_boundary(self):
        g, h = fixture(words=1024)
        g['tasks'] = g['tasks'][:1]
        del g['values']['b.out']
        g['outputs'] = []
        bindings = {'a': 'left'}
        for i in range(65):
            tid = f'use{i}'
            g['tasks'].append({'id': tid, 'op': 'add', 'numeric': 'test-int16',
                               'inputs': ['a.out'], 'outputs': [tid + '.out']})
            g['values'][tid + '.out'] = {'words': 1, 'producer': tid}
            bindings[tid] = 'right'
        initial = serial_seed(g, h, bindings)
        p = optimize(g, h, initial=initial, seconds=0.05, rounds=1)
        row, = p['optimization_history']
        self.assertEqual(len(row['open_tasks']), 66)
        self.assertEqual(len(row['coupled_binding_families'][0]), 65)
        verify(g, h, p)


if __name__ == '__main__':
    unittest.main()
