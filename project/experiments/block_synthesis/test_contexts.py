"""Context/format invariant tests; artificial durations are not IP evidence."""
from copy import deepcopy
import unittest

from contexts import serial_order
from numeric import Format, pack, unpack, convert_reference, conversion
from solver import Planner, optimize
from verify import verify, InvalidPlan
from test_solver import fixture


class TestContexts(unittest.TestCase):
    def fixture(self):
        g, h = fixture()
        g['state_groups'] = [{'id': 'M-accumulation', 'tasks': ['a', 'b']}]
        for site, s in h['services'].items():
            s['state_resource'] = site + '.state'
            h['resources'][site + '.state'] = 1
        return g, h

    def test_context_does_not_migrate_between_k_partitions(self):
        g, h = self.fixture()
        p = Planner(g, h).solve(2, 1)
        self.assertTrue(verify(g, h, p)['passed'])
        self.assertEqual(p['tasks']['a']['site'], p['tasks']['b']['site'])
        impossible = Planner(g, h, fixed={'a': 'left', 'b': 'right'}).solve(2, 1)
        self.assertNotIn('tasks', impossible)

    def test_independent_verifier_rejects_context_migration(self):
        g, h = fixture()
        p = Planner(g, h, fixed={'a': 'left', 'b': 'right'}).solve(2, 1)
        for site, service in h['services'].items():
            service['state_resource'] = site + '.state'
            h['resources'][site + '.state'] = 1
        g['state_groups'] = [{'tasks': ['a', 'b']}]
        with self.assertRaisesRegex(InvalidPlan, 'context migrated'):
            verify(g, h, p)

    def test_context_held_across_gap_and_blocks_competing_program(self):
        g, h = self.fixture()
        g['tasks'].append({'id': 'other', 'op': 'add', 'numeric': 'test-int16',
                           'inputs': ['input'], 'outputs': []})
        p = Planner(g, h, fixed={'a': 'left', 'b': 'left', 'other': 'left'}).solve(2, 1)
        self.assertTrue(verify(g, h, p)['passed'])
        a, b, c = (p['tasks'][n] for n in ('a', 'b', 'other'))
        self.assertTrue(c['end'] <= a['start'] or c['start'] >= b['end'])
        seed = optimize(g, h, rounds=0, seconds=2)
        self.assertTrue(verify(g, h, seed)['passed'])

    def test_context_seed_groups_commands_without_dropping_precedence(self):
        g, _ = self.fixture()
        g['tasks'].insert(1, {'id': 'independent', 'inputs': [], 'outputs': []})
        self.assertEqual(serial_order(g), ['a', 'b', 'independent'])
        bad = deepcopy(g)
        bad['state_groups'].append({'tasks': ['a']})
        with self.assertRaises(ValueError):
            serial_order(bad)

    def test_negative_rne_ties_and_compact_record_roundtrip(self):
        source, target = Format(32, -16, 4), Format(16, -10, 4)
        values = [-160, -96, 96, 160, -(1 << 31), (1 << 31)-1]
        result, recipe = convert_reference(values, source, target)
        self.assertEqual(result, [-2, -2, 2, 2, -32768, 32767])
        self.assertEqual(recipe['op'], 13)
        self.assertEqual(unpack(pack(result, target), target, len(result)), result)
        with self.assertRaisesRegex(ValueError, 'record expansion'):
            conversion(target, Format(16, -10, 2))
        with self.assertRaises(ValueError):
            pack([32768], target)


if __name__ == '__main__':
    unittest.main()
